type SpeakingCallback = (speaking: boolean) => void;

class MomoVoiceEngine {
  private isEnabled: boolean = true;
  private currentUtterance: SpeechSynthesisUtterance | null = null;
  private listeners: Set<SpeakingCallback> = new Set();
  private selectedVoice: SpeechSynthesisVoice | null = null;
  private speechRate: number = 1.0;
  private speechPitch: number = 1.0;
  private speechVolume: number = 1.0;

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
      // Remove markdown bold/italic
      .replace(/[*_#`~]/g, '')
      // Remove links
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      // Remove emojis/emoticons to sound clean
      .replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  public speak(text: string, onEnd?: () => void) {
    if (!this.isEnabled || typeof window === 'undefined' || !('speechSynthesis' in window)) {
      onEnd?.();
      return;
    }

    // Cancel any previous speech
    this.stop();

    const cleanText = this.cleanTextForSpeech(text);
    if (!cleanText) {
      onEnd?.();
      return;
    }

    const utterance = new SpeechSynthesisUtterance(cleanText);
    if (this.selectedVoice) {
      utterance.voice = this.selectedVoice;
    }
    utterance.rate = this.speechRate;
    utterance.pitch = this.speechPitch;
    utterance.volume = this.speechVolume;

    utterance.onstart = () => {
      this.notifyListeners(true);
    };

    utterance.onend = () => {
      this.notifyListeners(false);
      this.currentUtterance = null;
      onEnd?.();
    };

    utterance.onerror = (err) => {
      console.warn('[MOMO-TTS] Speech synthesis error:', err);
      this.notifyListeners(false);
      this.currentUtterance = null;
      onEnd?.();
    };

    this.currentUtterance = utterance;
    window.speechSynthesis.speak(utterance);
  }

  public stop() {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      this.currentUtterance = null;
      this.notifyListeners(false);
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
}

export const voiceEngine = new MomoVoiceEngine();
