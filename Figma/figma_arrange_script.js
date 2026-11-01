// ============================================================
//  IWM — Auto Arrange + Prototype Setup Script
//  Paste this in: Figma → Plugins → Development → Console
//  OR: Right-click canvas → Plugins → Run last plugin
// ============================================================

(async () => {
  const page = figma.currentPage;

  // ── 1. Get all top-level frames, sort by name ─────────────
  let frames = page.children
    .filter(n => n.type === "FRAME" || n.type === "GROUP" || n.type === "RECTANGLE")
    .sort((a, b) => a.name.localeCompare(b.name));

  if (frames.length === 0) {
    figma.notify("❌ No frames found on this page!", { error: true });
    return;
  }

  // ── 2. Resize all frames to consistent width (1440 × auto) ─
  const TARGET_W = 1440;
  const GAP      = 120;   // space between frames
  const TOP_Y    = 100;   // top margin

  let currentX = 100; // left start margin

  for (let i = 0; i < frames.length; i++) {
    const frame = frames[i];

    // Scale to 1440 width maintaining aspect ratio
    const scale = TARGET_W / frame.width;
    frame.resize(TARGET_W, Math.round(frame.height * scale));

    // Position horizontally
    frame.x = currentX;
    frame.y = TOP_Y;

    currentX += TARGET_W + GAP;
  }

  // ── 3. Zoom to fit all frames ─────────────────────────────
  figma.viewport.scrollAndZoomIntoView(frames);

  // ── 4. Add prototype connections (each → next) ────────────
  let linkedCount = 0;

  for (let i = 0; i < frames.length - 1; i++) {
    const currentFrame = frames[i];
    const nextFrame    = frames[i + 1];

    try {
      // Add a click → navigate reaction on the frame itself
      const reaction = {
        action: {
          type: "NODE",
          destinationId: nextFrame.id,
          navigation: "NAVIGATE",
          transition: {
            type: "SMART_ANIMATE",
            easing: { type: "EASE_OUT" },
            duration: 0.3
          },
          preserveScrollPosition: false
        },
        trigger: { type: "ON_CLICK" }
      };

      currentFrame.reactions = [reaction];
      linkedCount++;
    } catch (e) {
      // skip if frame type doesn't support reactions
    }
  }

  // ── 5. Done ───────────────────────────────────────────────
  figma.notify(
    `✅ ${frames.length} screens arranged! ${linkedCount} prototype links added.`,
    { timeout: 5000 }
  );

  console.log(`\n✅ IWM Figma Setup Complete`);
  console.log(`   Frames arranged : ${frames.length}`);
  console.log(`   Prototype links : ${linkedCount}`);
  console.log(`   Canvas width    : ${currentX}px`);
  console.log(`\n   Next steps:`);
  console.log(`   1. Click "Prototype" tab (top right)`);
  console.log(`   2. Set Starting Frame = 01_Login`);
  console.log(`   3. Click ▶ Present button to preview`);
  console.log(`   4. Share prototype link with client`);

})();
