package net.freyta.smw;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.MotionEvent;
import android.view.View;

/**
 * Native SMW 12-button touch gamepad. Multitouch, diagonals, slide-to-change,
 * and rotation are handled in one view so no key events fight Bluetooth input.
 * The transparent central region leaves the game visible.
 */
public final class TouchControlsView extends View {
    // SNES input bit positions used by main.c:kKbdRemap.
    public static final int A = 1 << 0;
    public static final int X = 1 << 1;
    public static final int SELECT = 1 << 2;
    public static final int START = 1 << 3;
    public static final int UP = 1 << 4;
    public static final int DOWN = 1 << 5;
    public static final int LEFT = 1 << 6;
    public static final int RIGHT = 1 << 7;
    public static final int B = 1 << 8;
    public static final int Y = 1 << 9;
    public static final int L = 1 << 10;
    public static final int R = 1 << 11;

    private static final int[] MASKS = { A, B, X, Y, L, R, SELECT, START };
    private static final String[] NAMES = { "A", "B", "X", "Y", "L", "R", "SELECT", "START" };
    private final RectF[] buttonRects = new RectF[MASKS.length];
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final MainActivity activity;
    private final RectF dpadRect = new RectF();
    private float padCx, padCy, padHalf;
    private int inputMask;
    private float density;
    private boolean portrait;

    public TouchControlsView(Context context) {
        super(context);
        activity = (MainActivity) context;
        density = getResources().getDisplayMetrics().density;
        for (int i = 0; i < buttonRects.length; i++)
            buttonRects[i] = new RectF();
        setWillNotDraw(false);
        setFocusable(false);
        setClickable(true);
    }

    private static float min(float a, float b) { return a < b ? a : b; }
    private static float max(float a, float b) { return a > b ? a : b; }

    private void place(int index, float x, float y, float rx, float ry) {
        buttonRects[index].set(x-rx, y-ry, x+rx, y+ry);
    }

    private void rebuild(int w, int h) {
        if (w <= 0 || h <= 0) return;
        portrait = h > w;
        float minTap = min(55*density, min(w,h)*.095f);
        if (!portrait) {
            // Match the native 256x224 integer scale: all buttons occupy
            // the free side columns, never the central picture.
            int gameScale = Math.max(1, Math.min(w / 256, h / 224));
            float side = (w - gameScale * 256f) * .5f;
            if (side < 40*density) side = max(80*density, w*.18f);
            float leftCx = side*.52f;
            float rightCx = w - side*.52f;
            padCx = leftCx;
            padCy = h*.60f;
            padHalf = min(side*.40f, h*.225f);
            float circle = min(side*.145f, h*.072f);
            circle = max(circle, minTap*.58f);
            circle = min(circle, side*.185f);
            float step = circle*1.83f;
            float facesY = h*.60f;
            place(0, rightCx+step, facesY, circle, circle); // A
            place(1, rightCx, facesY+step, circle, circle); // B
            place(2, rightCx, facesY-step, circle, circle); // X
            place(3, rightCx-step, facesY, circle, circle); // Y
            place(4, leftCx, h*.19f, min(side*.24f, 56*density), min(circle*.72f, 35*density));
            place(5, rightCx, h*.19f, min(side*.24f, 56*density), min(circle*.72f, 35*density));
            float pillW = min(side*.30f, 62*density);
            float pillH = max(18*density, circle*.39f);
            place(6, leftCx, h*.91f, pillW, pillH);
            place(7, rightCx, h*.91f, pillW, pillH);
        } else {
            // Game is in the upper 62% of the SDL window.
            // Reserve the bottom for large controls with no picture overlap.
            padCx = w*.25f;
            padCy = h*.79f;
            padHalf = min(w*.195f, h*.100f);
            float faceCx = w*.75f;
            float faceCy = h*.79f;
            float circle = min(w*.071f, h*.039f);
            circle = max(circle, minTap*.54f);
            float step = circle*1.80f;
            place(0, faceCx+step, faceCy, circle, circle);
            place(1, faceCx, faceCy+step, circle, circle);
            place(2, faceCx, faceCy-step, circle, circle);
            place(3, faceCx-step, faceCy, circle, circle);
            float shoulderW = min(w*.155f, 70*density);
            float shoulderH = min(h*.020f, 28*density);
            place(4, w*.21f, h*.655f, shoulderW, shoulderH);
            place(5, w*.79f, h*.655f, shoulderW, shoulderH);
            float pillW = min(w*.115f, 60*density);
            float pillH = min(h*.024f, 26*density);
            place(6, w*.40f, h*.947f, pillW, pillH);
            place(7, w*.60f, h*.947f, pillW, pillH);
        }
        dpadRect.set(padCx-padHalf, padCy-padHalf, padCx+padHalf, padCy+padHalf);
    }

    @Override protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);
        rebuild(w, h);
        clearButtons();
    }

    private void color(int c, Paint.Style style, float stroke) {
        paint.setColor(c);
        paint.setStyle(style);
        paint.setStrokeWidth(stroke);
    }

    private void drawButton(Canvas canvas, RectF rect, String name, boolean down) {
        color(down ? Color.argb(220, 67, 195, 204) : Color.argb(152, 12, 26, 58),
                Paint.Style.FILL, 1);
        float r = min(rect.width(), rect.height()) * .40f;
        canvas.drawRoundRect(rect, r, r, paint);
        color(Color.argb(235, 222, 246, 248), Paint.Style.STROKE, 2*density);
        canvas.drawRoundRect(rect, r, r, paint);
        paint.setStyle(Paint.Style.FILL);
        paint.setTypeface(android.graphics.Typeface.create("sans-serif", android.graphics.Typeface.BOLD));
        paint.setTextAlign(Paint.Align.CENTER);
        float desired = name.length() > 3 ? min(rect.height()*.38f, 12*density) : min(rect.height()*.55f, 20*density);
        paint.setTextSize(max(10*density, desired));
        Paint.FontMetrics m = paint.getFontMetrics();
        canvas.drawText(name, rect.centerX(), rect.centerY() - (m.ascent+m.descent)/2, paint);
    }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (getWidth() == 0 || getHeight() == 0) return;
        for (int i = 0; i < MASKS.length; i++)
            drawButton(canvas, buttonRects[i], NAMES[i], (inputMask & MASKS[i]) != 0);

        // Four independent surfaces to show diagonals when sliding the thumb.
        float third = padHalf / 2.65f;
        float wing = padHalf*.46f;
        drawButton(canvas, new RectF(padCx-third, padCy-padHalf,
                padCx+third, padCy-wing*.25f), "\u25b2", (inputMask & UP) != 0);
        drawButton(canvas, new RectF(padCx-third, padCy+wing*.25f,
                padCx+third, padCy+padHalf), "\u25bc", (inputMask & DOWN) != 0);
        drawButton(canvas, new RectF(padCx-padHalf, padCy-third,
                padCx-wing*.25f, padCy+third), "\u25c0", (inputMask & LEFT) != 0);
        drawButton(canvas, new RectF(padCx+wing*.25f, padCy-third,
                padCx+padHalf, padCy+third), "\u25b6", (inputMask & RIGHT) != 0);
    }

    private int hit(float x, float y) {
        int hit = 0;
        if (dpadRect.contains(x, y)) {
            float dx = (x-padCx) / padHalf;
            float dy = (y-padCy) / padHalf;
            // Intentionally permit diagonal inputs for running and flying.
            if (dx <= -.22f) hit |= LEFT;
            if (dx >=  .22f) hit |= RIGHT;
            if (dy <= -.22f) hit |= UP;
            if (dy >=  .22f) hit |= DOWN;
        }
        for (int i = 0; i < buttonRects.length; i++)
            if (buttonRects[i].contains(x, y)) hit |= MASKS[i];
        return hit;
    }

    private void sendMask(int mask) {
        if (inputMask == mask) return;
        inputMask = mask;
        activity.updateTouchButtons(mask);
        invalidate();
    }

    @Override public boolean onTouchEvent(MotionEvent event) {
        int action = event.getActionMasked();
        if (action == MotionEvent.ACTION_CANCEL) {
            clearButtons();
            return true;
        }
        int releasing = action == MotionEvent.ACTION_POINTER_UP || action == MotionEvent.ACTION_UP
                ? event.getActionIndex() : -1;
        int mask = 0;
        for (int i = 0; i < event.getPointerCount(); i++)
            if (i != releasing) mask |= hit(event.getX(i), event.getY(i));
        sendMask(mask);
        return true;
    }

    public void clearButtons() {
        sendMask(0);
    }
}
