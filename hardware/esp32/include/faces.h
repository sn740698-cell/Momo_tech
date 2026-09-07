#ifndef FACES_H
#define FACES_H

#include <U8g2lib.h>

// Procedural expression drawing routines for SSD1306 128x64 OLED
// Avoids heavy PROGMEM bitmap storage while yielding clean vector eyes and mouth

inline void drawFaceNormal(U8G2 &u8g2) {
    // Left eye
    u8g2.drawDisc(40, 28, 9, U8G2_DRAW_ALL);
    u8g2.setDrawColor(0);
    u8g2.drawDisc(38, 26, 3, U8G2_DRAW_ALL); // pupil highlight
    u8g2.setDrawColor(1);

    // Right eye
    u8g2.drawDisc(88, 28, 9, U8G2_DRAW_ALL);
    u8g2.setDrawColor(0);
    u8g2.drawDisc(86, 26, 3, U8G2_DRAW_ALL);
    u8g2.setDrawColor(1);

    // Gentle smile
    u8g2.drawCircle(64, 42, 10, U8G2_DRAW_LOWER_RIGHT | U8G2_DRAW_LOWER_LEFT);
}

inline void drawFaceHappy(U8G2 &u8g2) {
    // Left curved happy eye ^
    u8g2.drawArc(40, 32, 12, 0, 180);
    u8g2.drawArc(40, 33, 12, 0, 180);

    // Right curved happy eye ^
    u8g2.drawArc(88, 32, 12, 0, 180);
    u8g2.drawArc(88, 33, 12, 0, 180);

    // Big happy open smile
    u8g2.drawDisc(64, 44, 12, U8G2_DRAW_LOWER_RIGHT | U8G2_DRAW_LOWER_LEFT);
    // Cheeks
    u8g2.drawCircle(22, 38, 4, U8G2_DRAW_ALL);
    u8g2.drawCircle(106, 38, 4, U8G2_DRAW_ALL);
}

inline void drawFaceThinking(U8G2 &u8g2) {
    // Eyes looking up-right
    u8g2.drawDisc(40, 24, 8, U8G2_DRAW_ALL);
    u8g2.drawDisc(88, 24, 8, U8G2_DRAW_ALL);

    // Flat thoughtful mouth
    u8g2.drawLine(56, 48, 72, 48);

    // Thinking bubbles
    u8g2.drawCircle(108, 16, 3, U8G2_DRAW_ALL);
    u8g2.drawCircle(118, 10, 5, U8G2_DRAW_ALL);
}

inline void drawFaceConfused(U8G2 &u8g2) {
    // Left eye big circle
    u8g2.drawDisc(38, 28, 11, U8G2_DRAW_ALL);
    // Right eye tiny dot
    u8g2.drawDisc(90, 28, 4, U8G2_DRAW_ALL);

    // Wobbly mouth ~
    u8g2.drawCircle(60, 48, 6, U8G2_DRAW_UPPER_RIGHT);
    u8g2.drawCircle(68, 48, 6, U8G2_DRAW_LOWER_LEFT);

    // Question mark
    u8g2.setFont(u8g2_font_helvB14_tr);
    u8g2.drawStr(108, 24, "?");
}

inline void drawFaceSleepy(U8G2 &u8g2) {
    // Droopy flat closed eyes - -
    u8g2.drawLine(28, 30, 52, 30);
    u8g2.drawLine(28, 31, 52, 31);

    u8g2.drawLine(76, 30, 100, 30);
    u8g2.drawLine(76, 31, 100, 31);

    // Small o mouth
    u8g2.drawCircle(64, 48, 4, U8G2_DRAW_ALL);

    // Zzz
    u8g2.setFont(u8g2_font_6x12_tr);
    u8g2.drawStr(104, 18, "Z");
    u8g2.drawStr(112, 12, "z");
}

inline void drawFaceExcited(U8G2 &u8g2) {
    // Star eyes ★ ★
    u8g2.drawDisc(40, 26, 10, U8G2_DRAW_ALL);
    u8g2.drawDisc(88, 26, 10, U8G2_DRAW_ALL);
    u8g2.setDrawColor(0);
    u8g2.drawDisc(36, 22, 4, U8G2_DRAW_ALL);
    u8g2.drawDisc(84, 22, 4, U8G2_DRAW_ALL);
    u8g2.setDrawColor(1);

    // Open excited smile :D
    u8g2.drawDisc(64, 42, 14, U8G2_DRAW_LOWER_RIGHT | U8G2_DRAW_LOWER_LEFT);
    u8g2.drawLine(50, 42, 78, 42);
}

inline void drawFaceSad(U8G2 &u8g2) {
    // Drooping curved eyes
    u8g2.drawArc(40, 24, 10, 180, 360);
    u8g2.drawArc(88, 24, 10, 180, 360);

    // Inverted frown
    u8g2.drawArc(64, 54, 10, 0, 180);
    // Tear
    u8g2.drawDisc(30, 42, 3, U8G2_DRAW_ALL);
}

inline void drawFacePlayful(U8G2 &u8g2) {
    // Left wink >
    u8g2.drawLine(30, 24, 46, 30);
    u8g2.drawLine(46, 30, 30, 36);

    // Right open eye
    u8g2.drawDisc(88, 28, 9, U8G2_DRAW_ALL);
    u8g2.setDrawColor(0);
    u8g2.drawDisc(86, 26, 3, U8G2_DRAW_ALL);
    u8g2.setDrawColor(1);

    // Tongue sticking out :P
    u8g2.drawCircle(64, 42, 10, U8G2_DRAW_LOWER_RIGHT | U8G2_DRAW_LOWER_LEFT);
    u8g2.drawDisc(64, 50, 5, U8G2_DRAW_LOWER_RIGHT | U8G2_DRAW_LOWER_LEFT);
}

inline void renderExpression(U8G2 &u8g2, const String &expression) {
    u8g2.clearBuffer();
    if (expression == "happy") drawFaceHappy(u8g2);
    else if (expression == "thinking") drawFaceThinking(u8g2);
    else if (expression == "confused") drawFaceConfused(u8g2);
    else if (expression == "sleepy") drawFaceSleepy(u8g2);
    else if (expression == "excited") drawFaceExcited(u8g2);
    else if (expression == "sad") drawFaceSad(u8g2);
    else if (expression == "playful") drawFacePlayful(u8g2);
    else drawFaceNormal(u8g2);
    u8g2.sendBuffer();
}

#endif // FACES_H
