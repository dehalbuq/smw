package com.dehalbuq.smwrecomp;

import android.os.Bundle;
import android.view.View;
import org.libsdl.app.SDLActivity;

/** Android TV activity with direct gamepad input and no virtual controls. */
public final class SMWActivity extends SDLActivity {
    @Override
    protected String[] getLibraries() {
        return new String[]{"SDL2", "main"};
    }

    private void immersive() {
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_FULLSCREEN |
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY |
            View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN |
            View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE
        );
    }

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        immersive();
    }

    @Override
    public void onWindowFocusChanged(boolean focus) {
        super.onWindowFocusChanged(focus);
        if (focus) immersive();
    }
}
