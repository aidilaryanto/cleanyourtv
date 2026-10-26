package com.gathin.tvhome;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.drawable.GradientDrawable;
import android.media.MediaMetadata;
import android.media.session.MediaController;
import android.media.session.MediaSessionManager;
import android.media.session.PlaybackState;
import android.text.TextUtils;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.List;

final class NowPlayingCard {
    private static final String TAG = "NowPlayingCard";

    private final Activity activity;
    private final float density;
    private final LinearLayout card;
    private final ImageView artwork;
    private final TextView title;
    private final TextView artist;
    private final TextView playButton;
    private MediaController activeController;

    NowPlayingCard(Activity activity, FrameLayout root) {
        this.activity = activity;
        density = activity.getResources().getDisplayMetrics().density;

        card = new LinearLayout(activity);
        card.setOrientation(LinearLayout.HORIZONTAL);
        card.setGravity(Gravity.CENTER_VERTICAL);
        int padding = (int) (7 * density);
        card.setPadding(padding, padding, (int) (14 * density), padding);

        GradientDrawable background = new GradientDrawable();
        background.setCornerRadius(16 * density);
        background.setColor(0x5518181C);
        background.setStroke((int) density, 0x33FFFFFF);
        card.setBackground(background);

        artwork = new ImageView(activity);
        artwork.setScaleType(ImageView.ScaleType.CENTER_CROP);
        artwork.setClipToOutline(true);
        GradientDrawable artworkBackground = new GradientDrawable();
        artworkBackground.setCornerRadius(10 * density);
        artwork.setBackground(artworkBackground);
        card.addView(artwork, new LinearLayout.LayoutParams(
                (int) (42 * density), (int) (42 * density)));

        LinearLayout metadata = new LinearLayout(activity);
        metadata.setOrientation(LinearLayout.VERTICAL);
        metadata.setPadding((int) (12 * density), 0, (int) (12 * density), 0);
        title = new TextView(activity);
        title.setTextColor(0xFFFFFFFF);
        title.setTextSize(14f);
        title.setSingleLine(true);
        title.setEllipsize(TextUtils.TruncateAt.END);
        artist = new TextView(activity);
        artist.setTextColor(0xAAFFFFFF);
        artist.setTextSize(11.5f);
        artist.setSingleLine(true);
        artist.setEllipsize(TextUtils.TruncateAt.END);
        metadata.addView(title);
        metadata.addView(artist);
        card.addView(metadata, new LinearLayout.LayoutParams((int) (155 * density), -2));

        int buttonSize = (int) (34 * density);
        int buttonMargin = (int) (4 * density);
        TextView previous = makeButton("|<", () -> {
            if (activeController != null) {
                activeController.getTransportControls().skipToPrevious();
            }
        });
        playButton = makeButton("||", () -> {
            if (activeController == null) return;
            PlaybackState state = activeController.getPlaybackState();
            if (state != null && state.getState() == PlaybackState.STATE_PLAYING) {
                activeController.getTransportControls().pause();
            } else {
                activeController.getTransportControls().play();
            }
            card.postDelayed(this::refresh, 300);
        });
        TextView next = makeButton(">|", () -> {
            if (activeController != null) {
                activeController.getTransportControls().skipToNext();
            }
        });
        addButton(previous, buttonSize, buttonMargin, buttonMargin);
        addButton(playButton, buttonSize, buttonMargin, buttonMargin);
        addButton(next, buttonSize, buttonMargin, 0);

        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT,
                FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.TOP | Gravity.LEFT);
        params.leftMargin = (int) (58 * density);
        params.topMargin = (int) (110 * density);
        card.setVisibility(View.GONE);
        root.addView(card, params);
    }

    private TextView makeButton(String label, Runnable action) {
        TextView button = new TextView(activity);
        button.setText(label);
        button.setTextSize(15f);
        button.setTextColor(0xCCFFFFFF);
        button.setGravity(Gravity.CENTER);
        button.setFocusable(true);
        button.setClickable(true);
        GradientDrawable background = new GradientDrawable();
        background.setCornerRadius(18 * density);
        background.setColor(0x1AFFFFFF);
        button.setBackground(background);
        button.setOnFocusChangeListener((view, focused) -> {
            background.setColor(focused ? 0xFFFFFFFF : 0x1AFFFFFF);
            button.setTextColor(focused ? 0xFF000000 : 0xCCFFFFFF);
            view.animate().scaleX(focused ? 1.12f : 1f)
                    .scaleY(focused ? 1.12f : 1f).setDuration(140).start();
        });
        button.setOnClickListener(view -> action.run());
        return button;
    }

    private void addButton(TextView button, int size, int leftMargin, int rightMargin) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(size, size);
        params.setMargins(leftMargin, 0, rightMargin, 0);
        card.addView(button, params);
    }

    void refresh() {
        MediaSessionManager manager =
                (MediaSessionManager) activity.getSystemService(Context.MEDIA_SESSION_SERVICE);
        if (manager == null) {
            activeController = null;
            card.setVisibility(View.GONE);
            return;
        }

        final List<MediaController> controllers;
        try {
            controllers = manager.getActiveSessions(new ComponentName(activity, GuardRevival.class));
        } catch (SecurityException e) {
            activeController = null;
            card.setVisibility(View.GONE);
            Log.w(TAG, "Notification-listener access is required for the Now Playing card.", e);
            return;
        }

        activeController = null;
        if (controllers != null) {
            for (MediaController controller : controllers) {
                MediaMetadata metadata = controller.getMetadata();
                if (metadata == null) continue;
                CharSequence trackTitle = metadata.getText(MediaMetadata.METADATA_KEY_TITLE);
                if (TextUtils.isEmpty(trackTitle)) continue;

                activeController = controller;
                title.setText(trackTitle);
                CharSequence trackArtist = metadata.getText(MediaMetadata.METADATA_KEY_ARTIST);
                artist.setText(TextUtils.isEmpty(trackArtist) ? "Now Playing" : trackArtist);

                Bitmap image = metadata.getBitmap(MediaMetadata.METADATA_KEY_ALBUM_ART);
                if (image == null) image = metadata.getBitmap(MediaMetadata.METADATA_KEY_ART);
                if (image == null) artwork.setImageResource(R.drawable.ic_av);
                else artwork.setImageBitmap(image);

                PlaybackState state = controller.getPlaybackState();
                playButton.setText(state != null && state.getState() == PlaybackState.STATE_PLAYING
                        ? "||" : ">");
                card.setVisibility(View.VISIBLE);
                return;
            }
        }
        card.setVisibility(View.GONE);
    }
}
