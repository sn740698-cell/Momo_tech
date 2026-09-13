type SpeakingCallback = (speaking: boolean) => void;
type RecognitionCallback = (transcript: string, isFinal: boolean) => void;
type RecognitionErrorCallback = (error: string) => void;
type RecognitionEndCallback = () => void;

class MomoVoiceEngine {
  private isEnabled: boolean = true;
  private currentUtterance: SpeechSynthesisUtterance | null = null;
  private listeners: Set<SpeakingCallback> = new Set();
  private selectedVoice: SpeechSynthesisVoice | null = null;
  private speechRate: number = 1.0;
  private speechPitch: number = 1.0;
  private speechVolume: number = 1.0;

  // TTS Chunking & Keep-Alive Watchdog against Windows/Chrome 15s freeze
  private utteranceQueue: string[] = [];
  private currentOnEnd: (() => void) | null = null;
  private keepAliveTimer: ReturnType<typeof setInterval> | null = null;

  // Speech Recognition (Speech-to-Text)
  private recognition: any = null;
  private listening: boolean = false;
  private onRecResult: RecognitionCallback | null = null;
  private onRecError: RecognitionErrorCallback | null = null;
  private onRecEnd: RecognitionEndCallback | null = null;

  constructor() {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      // Load available browser voices
      window.speechSynthesis.onvoiceschanged = () => {
        this.selectBestVoice();
      };
      this.selectBestVoice();
    }
  }

  private selectBestVoice() {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    const voices = window.speechSynthesis.getVoices();
    // Prefer natural, English voices (e.g. Zira, David, Samantha, Natural)
    const preferred = voices.find(
      (v) =>
        v.lang.startsWith('en') &&
        (v.name.includes('Natural') || v.name.includes('Zira') || v.name.includes('Samantha') || v.name.includes('Google') || v.name.includes('David'))
    );
    this.selectedVoice = preferred || voices.find((v) => v.lang.startsWith('en')) || voices[0] || null;
  }

  public getVoices(): SpeechSynthesisVoice[] {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return [];
    return window.speechSynthesis.getVoices().filter((v) => v.lang.startsWith('en'));
  }

  public setVoice(voiceName: string) {
    const voices = this.getVoices();
    const match = voices.find((v) => v.name === voiceName);
    if (match) this.selectedVoice = match;
  }

  public cleanTextForSpeech(text: string): string {
    return text
      // Remove code blocks
      .replace(/```[\s\S]*?```/g, 'Code block omitted.')
      // Remove inline code
      .replace(/`[^`]*`/g, '')
      // Remove markdown links, keep text
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      // Remove raw URLs
      .replace(/https?:\/\/\S+/g, '')
      // Strip bullet points at start of line
      .replace(/^[\s]*[•\-\*]\s+/gm, '')
      // Strip numbered list indicators at start of line
      .replace(/^[\s]*\d+\.\s+/gm, '')
      // Strip blockquotes
      .replace(/^[\s]*>\s+/gm, '')
      // Remove markdown bold/italic/strikethrough/headers
      .replace(/[*_#~]/g, '')
      // Remove emojis/emoticons to sound clean
      .replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '')
      // Normalize whitespace
      .replace(/\s+/g, ' ')
      .trim();
  }

  /**
   * Splits long text into natural sentence/clause chunks (<160 chars)
   * to eliminate the Windows/Chromium 15-second SpeechSynthesis freeze.
   */
  private splitIntoChunks(text: string): string[] {
    const rawMatches = text.match(/[^.!?;\n]+[.!?;\n]+|[^.!?;\n]+$/g);
    if (!rawMatches) return [text];

    const chunks: string[] = [];
    let currentChunk = '';

    for (const match of rawMatches) {
      const piece = match.trim();
      if (!piece) continue;

      if ((currentChunk + ' ' + piece).trim().length <= 160) {
        currentChunk = (currentChunk + ' ' + piece).trim();
      } else {
        if (currentChunk) chunks.push(currentChunk);
        if (piece.length <= 160) {
          currentChunk = piece;
        } else {
          // Break large sentence by commas or words
          const words = piece.split(' ');
          let sub = '';
          for (const w of words) {
            if ((sub + ' ' + w).length <= 160) {
              sub = (sub + ' ' + w).trim();
            } else {
              if (sub) chunks.push(sub);
              sub = w;
            }
          }
          currentChunk = sub;
        }
      }
    }
    if (currentChunk) chunks.push(currentChunk);
    return chunks.length > 0 ? chunks : [text];
  }

  private startKeepAlive() {
    this.stopKeepAlive();
    // Chromium SpeechSynthesis watchdog prevents silent freeze after ~15 seconds
    this.keepAliveTimer = setInterval(() => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window && window.speechSynthesis.speaking) {
        window.speechSynthesis.pause();
        window.speechSynthesis.resume();
      }
    }, 8000);
  }

  private stopKeepAlive() {
    if (this.keepAliveTimer) {
      clearInterval(this.keepAliveTimer);
      this.keepAliveTimer = null;
    }
  }

  public speak(text: string, onEnd?: () => void) {
    if (!this.isEnabled || typeof window === 'undefined' || !('speechSynthesis' in window)) {
      onEnd?.();
      return;
    }

    // Cancel any ongoing speech
    this.stop();

    const cleanText = this.cleanTextForSpeech(text);
    if (!cleanText) {
      onEnd?.();
      return;
    }

    this.utteranceQueue = this.splitIntoChunks(cleanText);
    this.currentOnEnd = onEnd || null;

    this.notifyListeners(true);
    this.startKeepAlive();
    this.playNextChunk();
  }

  private playNextChunk() {
    if (this.utteranceQueue.length === 0) {
      this.finishSpeech();
      return;
    }

    const chunk = this.utteranceQueue.shift();
    if (!chunk) {
      this.playNextChunk();
      return;
    }

    const utterance = new SpeechSynthesisUtterance(chunk);
    if (this.selectedVoice) {
      utterance.voice = this.selectedVoice;
    }
    utterance.rate = this.speechRate;
    utterance.pitch = this.speechPitch;
    utterance.volume = this.speechVolume;

    utterance.onend = () => {
      if (this.utteranceQueue.length > 0) {
        this.playNextChunk();
      } else {
        this.finishSpeech();
      }
    };

    utterance.onerror = (err) => {
      if (err.error !== 'interrupted' && err.error !== 'canceled') {
        console.warn('[MOMO-TTS] Chunk speech error:', err);
      }
      this.finishSpeech();
    };

    this.currentUtterance = utterance;
    window.speechSynthesis.speak(utterance);
  }

  private finishSpeech() {
    this.stopKeepAlive();
    this.currentUtterance = null;
    this.notifyListeners(false);
    if (this.currentOnEnd) {
      const cb = this.currentOnEnd;
      this.currentOnEnd = null;
      cb();
    }
  }

  public stop() {
    this.utteranceQueue = [];
    this.stopKeepAlive();
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      this.currentUtterance = null;
      this.notifyListeners(false);
    }
    if (this.currentOnEnd) {
      const cb = this.currentOnEnd;
      this.currentOnEnd = null;
      cb();
    }
  }

  public toggleVoice(): boolean {
    this.isEnabled = !this.isEnabled;
    if (!this.isEnabled) {
      this.stop();
    }
    return this.isEnabled;
  }

  public isVoiceEnabled(): boolean {
    return this.isEnabled;
  }

  public setVoiceEnabled(enabled: boolean) {
    this.isEnabled = enabled;
    if (!enabled) this.stop();
  }

  public onSpeakingChange(callback: SpeakingCallback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  private notifyListeners(isSpeaking: boolean) {
    this.listeners.forEach((cb) => {
      try {
        cb(isSpeaking);
      } catch (e) {
        console.error(e);
      }
    });
  }

  // =========================================================================
  // VOICE RECOGNITION (SPEECH-TO-TEXT / STT)
  // =========================================================================

  public isRecognitionSupported(): boolean {
    if (typeof window === 'undefined') return false;
    return !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
  }

  public isListening(): boolean {
    return this.listening;
  }

  public startListening(
    onResult: RecognitionCallback,
    onError?: RecognitionErrorCallback,
    onEnd?: RecognitionEndCallback
  ): boolean {
    if (!this.isRecognitionSupported()) {
      onError?.('Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.');
      return false;
    }

    this.stopListening();

    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    try {
      this.recognition = new SpeechRec();
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.lang = 'en-US';

      this.onRecResult = onResult;
      this.onRecError = onError || null;
      this.onRecEnd = onEnd || null;
      this.listening = true;

      this.recognition.onresult = (event: any) => {
        let interim = '';
        let final = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const res = event.results[i];
          const text = res[0]?.transcript || '';
          if (res.isFinal) {
            final += text;
          } else {
            interim += text;
          }
        }

        const combined = (final || interim).trim();
        if (combined && this.onRecResult) {
          this.onRecResult(combined, Boolean(final));
        }
      };

      this.recognition.onerror = (event: any) => {
        const error = event.error || 'Speech recognition error';
        if (error !== 'no-speech') {
          console.warn('[MOMO-STT] Speech recognition error:', error);
          if (this.onRecError) this.onRecError(error);
        }
      };

      this.recognition.onend = () => {
        this.listening = false;
        if (this.onRecEnd) this.onRecEnd();
      };

      this.recognition.start();
      return true;
    } catch (err: any) {
      this.listening = false;
      console.error('[MOMO-STT] Failed to start speech recognition:', err);
      onError?.(err?.message || 'Failed to start speech recognition');
      return false;
    }
  }

  public stopListening() {
    this.listening = false;
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch {
        // Ignored
      }
      this.recognition = null;
    }
  }
}

export const voiceEngine = new MomoVoiceEngine();
