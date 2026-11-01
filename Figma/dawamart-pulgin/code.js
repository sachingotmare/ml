figma.showUI(__html__, { width: 380, height: 300 });

figma.ui.onmessage = async msg => {
  if (msg.type === 'generate') {
    try {
      await loadFonts();
      await generateAll();
      figma.ui.postMessage({ type: 'done' });
    } catch (e) {
      figma.notify('Error: ' + e.message, { error: true });
      figma.ui.postMessage({ type: 'error', message: e.message });
    }
  }
  if (msg.type === 'cancel') figma.closePlugin();
};

async function loadFonts() {
  await Promise.all([
    figma.loadFontAsync({ family: 'Inter', style: 'Regular' }),
    figma.loadFontAsync({ family: 'Inter', style: 'Medium' }),
    figma.loadFontAsync({ family: 'Inter', style: 'Semi Bold' }),
    figma.loadFontAsync({ family: 'Inter', style: 'Bold' }),
  ]);
}

// ─── COLOR PALETTE ─────────────────────────────────────────────
const C = {
  blue:      { r: 0.145, g: 0.388, b: 0.922 },
  blueLight: { r: 0.800, g: 0.878, b: 0.988 },
  bluePale:  { r: 0.929, g: 0.949, b: 0.996 },
  white:     { r: 1,     g: 1,     b: 1     },
  dark:      { r: 0.071, g: 0.114, b: 0.196 },
  mid:       { r: 0.282, g: 0.333, b: 0.408 },
  gray:      { r: 0.427, g: 0.482, b: 0.557 },
  lgray:     { r: 0.820, g: 0.851, b: 0.894 },
  xlight:    { r: 0.929, g: 0.949, b: 0.965 },
  green:     { r: 0.133, g: 0.773, b: 0.369 },
  greenPale: { r: 0.878, g: 0.969, b: 0.906 },
  red:       { r: 0.937, g: 0.267, b: 0.267 },
  redPale:   { r: 0.996, g: 0.878, b: 0.878 },
  amber:     { r: 0.961, g: 0.620, b: 0.043 },
  amberPale: { r: 1.000, g: 0.945, b: 0.878 },
  bg:        { r: 0.973, g: 0.980, b: 0.988 },
  blueMid:   { r: 0.302, g: 0.502, b: 0.949 },
};

// ─── PRIMITIVE HELPERS ─────────────────────────────────────────
function R(parent, x, y, w, h, fill, radius, opts) {
  radius = radius || 0; opts = opts || {};
  const r = figma.createRectangle();
  r.x = x; r.y = y; r.resize(Math.max(w, 1), Math.max(h, 1));
  r.fills = [{ type: 'SOLID', color: fill }];
  if (radius) r.cornerRadius = radius;
  if (opts.opacity !== undefined) r.opacity = opts.opacity;
  if (opts.stroke) { r.strokes = [{ type: 'SOLID', color: opts.stroke }]; r.strokeWeight = opts.sw || 1; }
  if (opts.dashes) r.dashPattern = opts.dashes;
  parent.appendChild(r);
  return r;
}

function T(parent, x, y, text, size, style, color, align, opts) {
  align = align || 'LEFT'; opts = opts || {};
  const t = figma.createText();
  t.x = x; t.y = y;
  t.fontName = { family: 'Inter', style: style };
  t.fontSize = size;
  t.characters = String(text);
  t.fills = [{ type: 'SOLID', color: color }];
  t.textAlignHorizontal = align;
  if (opts.opacity !== undefined) t.opacity = opts.opacity;
  parent.appendChild(t);
  return t;
}

function screen(name, bg) {
  bg = bg || C.bg;
  const f = figma.createFrame();
  f.name = name;
  f.resize(375, 812);
  f.fills = [{ type: 'SOLID', color: bg }];
  f.clipsContent = true;
  return f;
}

function ln(parent, x, y, w) {
  R(parent, x, y, w, 1, C.lgray);
}

// ─── SHARED COMPONENTS ──────────────────────────────────────────
function statusBar(f, white) {
  const col = white ? C.white : C.dark;
  T(f, 16, 14, '9:41', 12, 'Semi Bold', col);
  T(f, 303, 14, '●●● ▲ ■', 11, 'Regular', col);
}

function topBar(f, title, rightLabel) {
  R(f, 0, 44, 375, 56, C.white);
  ln(f, 0, 99, 375);
  R(f, 20, 56, 32, 32, C.bluePale, 8);
  T(f, 29, 61, '←', 14, 'Bold', C.blue);
  T(f, 62, 62, title, 17, 'Semi Bold', C.dark);
  if (rightLabel) T(f, 305, 64, rightLabel, 12, 'Semi Bold', C.blue);
}

function bottomNav(f, active) {
  active = active || 0;
  R(f, 0, 732, 375, 80, C.white);
  ln(f, 0, 732, 375);
  var tabs = [['🏠','Home'],['🔍','Search'],['🛒','Cart'],['📦','Orders'],['👤','Profile']];
  tabs.forEach(function(tab, i) {
    var cx = 37.5 + i * 75;
    var isA = i === active;
    T(f, cx - 10, 746, tab[0], 20, 'Regular', isA ? C.blue : C.gray);
    T(f, cx - tab[1].length * 3, 772, tab[1], 10, isA ? 'Semi Bold' : 'Regular', isA ? C.blue : C.gray);
  });
}

function pharmNav(f, active) {
  active = active || 0;
  R(f, 0, 732, 375, 80, C.white);
  ln(f, 0, 732, 375);
  var tabs = [['🏠','Dashboard'],['📦','Orders'],['📋','Inventory'],['👤','Profile']];
  tabs.forEach(function(tab, i) {
    var cx = 47 + i * 95;
    var isA = i === active;
    T(f, cx - 10, 746, tab[0], 20, 'Regular', isA ? C.blue : C.gray);
    T(f, cx - tab[1].length * 3, 772, tab[1], 10, isA ? 'Semi Bold' : 'Regular', isA ? C.blue : C.gray);
  });
}

function inputField(f, x, y, placeholder, active) {
  R(f, x, y, 335, 50, C.white, 12, { stroke: active ? C.blue : C.lgray, sw: active ? 2 : 1 });
  T(f, x + 16, y + 17, placeholder, 14, 'Regular', C.gray);
}

function cardBox(f, x, y, w, h) {
  return R(f, x, y, w, h, C.white, 14, { stroke: C.lgray, sw: 0.5 });
}

function primaryBtn(f, x, y, w, label) {
  R(f, x, y, w, 50, C.blue, 14);
  T(f, x + w / 2 - label.length * 4.2, y + 16, label, 15, 'Semi Bold', C.white);
}

function outlineBtn(f, x, y, w, label) {
  R(f, x, y, w, 50, C.white, 14, { stroke: C.lgray, sw: 1 });
  T(f, x + w / 2 - label.length * 4, y + 16, label, 15, 'Semi Bold', C.dark);
}

function addHotspot(frame, dest) {
  if (!dest) return;
  frame.reactions = [{
    trigger: { type: 'ON_CLICK' },
    actions: [{
      type: 'NODE',
      destinationId: dest.id,
      navigation: 'NAVIGATE',
      transition: null
    }]
  }];
}

// ═══════════════════════════════════════════════════════════════
// CUSTOMER APP — 12 SCREENS
// ═══════════════════════════════════════════════════════════════

function C01_Splash() {
  var f = screen('C01 · Splash', C.blue);
  R(f, 40, 80, 295, 295, C.white, 148, { opacity: 0.06 });
  R(f, 131.5, 180, 112, 112, C.white, 24);
  R(f, 179.5, 200, 16, 72, C.blue, 4);
  R(f, 151.5, 228, 72, 16, C.blue, 4);
  T(f, 100, 316, 'DawaMart', 32, 'Bold', C.white, 'CENTER');
  T(f, 50, 362, 'Your Health, Our Priority.', 14, 'Regular', C.blueLight, 'CENTER');
  R(f, 117.5, 490, 140, 6, C.white, 3, { opacity: 0.3 });
  R(f, 117.5, 490, 88, 6, C.white, 3);
  T(f, 148, 504, 'Loading…', 11, 'Regular', C.blueLight, 'CENTER');
  return f;
}

function C02_Login() {
  var f = screen('C02 · Login / Register');
  statusBar(f);
  R(f, 155.5, 60, 64, 64, C.bluePale, 16);
  R(f, 183.5, 72, 8, 40, C.blue, 2);
  R(f, 167.5, 88, 40, 8, C.blue, 2);
  T(f, 98, 142, 'Welcome Back! 👋', 22, 'Bold', C.dark);
  T(f, 20, 174, 'Sign in to continue', 14, 'Regular', C.gray);
  // Tabs
  R(f, 20, 208, 163, 42, C.blue, 10);
  T(f, 74, 220, 'Login', 15, 'Semi Bold', C.white);
  R(f, 192, 208, 163, 42, C.xlight, 10);
  T(f, 230, 220, 'Register', 15, 'Semi Bold', C.gray);
  inputField(f, 20, 268, '📱  Mobile Number');
  inputField(f, 20, 332, '🔒  Password');
  T(f, 234, 396, 'Forgot Password?', 13, 'Semi Bold', C.blue);
  primaryBtn(f, 20, 424, 335, 'Login');
  ln(f, 20, 490, 140);
  T(f, 170, 480, 'or', 13, 'Regular', C.gray);
  ln(f, 200, 490, 135);
  R(f, 20, 510, 160, 48, C.white, 12, { stroke: C.lgray, sw: 1 });
  T(f, 52, 525, 'G  Google', 13, 'Semi Bold', C.dark);
  R(f, 195, 510, 160, 48, C.white, 12, { stroke: C.lgray, sw: 1 });
  T(f, 218, 525, 'f  Facebook', 13, 'Semi Bold', C.dark);
  T(f, 60, 580, "Don't have an account? ", 14, 'Regular', C.gray);
  T(f, 248, 580, 'Register', 14, 'Semi Bold', C.blue);
  return f;
}

function C03_Home() {
  var f = screen('C03 · Home Dashboard');
  statusBar(f);
  R(f, 0, 44, 375, 62, C.white);
  ln(f, 0, 105, 375);
  R(f, 20, 60, 14, 14, C.blue, 7);
  T(f, 40, 58, 'Mumbai, 440001  ▾', 13, 'Semi Bold', C.dark);
  R(f, 321, 57, 24, 24, C.bluePale, 12);
  T(f, 326, 59, '🔔', 14, 'Regular', C.dark);
  // Search bar
  R(f, 20, 122, 335, 46, C.white, 23, { stroke: C.lgray, sw: 1 });
  T(f, 38, 134, '🔍  Search medicines, healthcare…', 14, 'Regular', C.gray);
  // Banner
  R(f, 20, 184, 335, 124, C.blue, 18);
  T(f, 38, 200, '20% OFF', 28, 'Bold', C.white);
  T(f, 38, 236, 'on all medicines today!', 14, 'Regular', C.blueLight);
  T(f, 38, 258, 'Use code: DAWA20', 11, 'Semi Bold', C.blueLight);
  R(f, 263, 196, 96, 104, C.blueMid, 12);
  T(f, 285, 224, '💊', 40, 'Regular', C.white);
  // Categories
  T(f, 20, 326, 'Categories', 16, 'Semi Bold', C.dark);
  T(f, 293, 328, 'View All →', 13, 'Regular', C.blue);
  var cats = [['💊','Medicin'],['❤️','Personal'],['👶','Baby'],['🩺','Diabete'],['🌿','Wellnes'],['🏥','Devices']];
  cats.forEach(function(cat, i) {
    var cx = 20 + i * 57;
    R(f, cx, 352, 50, 50, C.bluePale, 14);
    T(f, cx + 11, 362, cat[0], 22, 'Regular', C.blue);
    T(f, cx - 2, 406, cat[1], 10, 'Regular', C.gray, 'CENTER');
  });
  T(f, 20, 430, 'Featured Medicines', 16, 'Semi Bold', C.dark);
  T(f, 293, 432, 'View All →', 13, 'Regular', C.blue);
  // Product cards
  var pCards = [[20,'Paracetamol 500mg','₹32.00','20% off'],[194,'Crocin 650mg','₹45.00','15% off']];
  pCards.forEach(function(pc) {
    cardBox(f, pc[0], 456, 160, 154);
    R(f, pc[0]+10, 464, 140, 78, C.bluePale, 10);
    T(f, pc[0]+50, 490, '💊', 28, 'Regular', C.blue);
    T(f, pc[0]+10, 548, pc[1], 12, 'Semi Bold', C.dark);
    T(f, pc[0]+10, 566, pc[2], 14, 'Bold', C.blue);
    T(f, pc[0]+80, 568, pc[3], 10, 'Regular', C.green);
    R(f, pc[0]+128, 582, 24, 22, C.blue, 6);
    T(f, pc[0]+134, 584, '+', 14, 'Bold', C.white);
  });
  // Rx CTA
  R(f, 20, 626, 335, 68, C.blue, 16, { opacity: 0.92 });
  T(f, 34, 638, '📋  Upload Prescription', 15, 'Semi Bold', C.white);
  T(f, 34, 660, 'Get medicines as prescribed', 12, 'Regular', C.blueLight);
  R(f, 283, 638, 62, 30, C.white, 8);
  T(f, 291, 644, 'Upload', 12, 'Semi Bold', C.blue);
  bottomNav(f, 0);
  return f;
}

function C04_Categories() {
  var f = screen('C04 · Categories');
  statusBar(f);
  topBar(f, 'Categories');
  R(f, 20, 112, 335, 40, C.white, 20, { stroke: C.lgray, sw: 1 });
  T(f, 36, 122, '🔍  Search categories…', 14, 'Regular', C.gray);
  var cats = [
    ['💊','All Medicines','1,200+ products'],
    ['📋','Prescription Medicines','450+ products'],
    ['❤️','Health Care','380+ products'],
    ['🌿','Personal Care','290+ products'],
    ['👶','Baby Care','210+ products'],
    ['🌱','Ayurveda','170+ products'],
    ['🔬','Devices & Accessories','95+ products'],
    ['💚','Vitamins & Supplements','320+ products'],
  ];
  cats.forEach(function(cat, i) {
    var y = 166 + i * 68;
    R(f, 20, y, 335, 58, C.white, 12, { stroke: C.lgray, sw: 0.5 });
    R(f, 30, y+9, 40, 40, C.bluePale, 10);
    T(f, 38, y+14, cat[0], 20, 'Regular', C.blue);
    T(f, 82, y+12, cat[1], 14, 'Semi Bold', C.dark);
    T(f, 82, y+32, cat[2], 12, 'Regular', C.gray);
    T(f, 342, y+18, '›', 18, 'Regular', C.gray);
  });
  T(f, 20, 718, 'Top Brands', 16, 'Semi Bold', C.dark);
  T(f, 290, 720, 'View All →', 13, 'Regular', C.blue);
  return f;
}

function C05_Search() {
  var f = screen('C05 · Search Results');
  statusBar(f);
  R(f, 20, 52, 285, 46, C.white, 23, { stroke: C.blue, sw: 2 });
  T(f, 36, 64, '🔍  paracetamol', 14, 'Regular', C.dark);
  R(f, 329, 52, 26, 46, C.bluePale, 13);
  T(f, 335, 64, '⚙', 14, 'Regular', C.blue);
  T(f, 20, 116, '12 Results Found', 14, 'Regular', C.gray);
  T(f, 237, 116, 'Sort: Relevance  ▾', 12, 'Semi Bold', C.blue);
  var chips = ['All','OTC','Rx','Generic','Branded'];
  chips.forEach(function(chip, i) {
    if (20 + i * 72 > 300) return;
    R(f, 20+i*72, 140, 66, 26, i===0 ? C.blue : C.white, 13, i>0 ? {stroke:C.lgray,sw:1} : {});
    T(f, 28+i*72, 147, chip, 12, i===0 ? 'Semi Bold' : 'Regular', i===0 ? C.white : C.gray);
  });
  var meds = [
    ['Paracetamol 500mg Tablet','GSK Pharma','★★★★☆  4.2','₹32.00'],
    ['Paracetamol 650mg','Cipla','★★★★☆  4.1','₹46.75'],
    ['Paracetamol Drops 15ml','Abbott','★★★★☆  4.4','₹68.00'],
    ['Paracetamol Syrup','Sun Pharma','★★★★☆  3.9','₹52.00'],
  ];
  meds.forEach(function(med, i) {
    var y = 178 + i * 108;
    cardBox(f, 20, y, 335, 100);
    R(f, 30, y+10, 80, 80, C.bluePale, 10);
    T(f, 50, y+24, '💊', 32, 'Regular', C.blue);
    T(f, 122, y+12, med[0], 13, 'Semi Bold', C.dark);
    T(f, 122, y+32, med[1], 11, 'Regular', C.gray);
    T(f, 122, y+50, med[2], 11, 'Regular', C.amber);
    T(f, 122, y+68, med[3], 14, 'Bold', C.blue);
    R(f, 303, y+62, 50, 26, C.blue, 8);
    T(f, 311, y+68, 'Add +', 12, 'Semi Bold', C.white);
  });
  bottomNav(f, 1);
  return f;
}

function C06_Product() {
  var f = screen('C06 · Product Details');
  statusBar(f);
  topBar(f, 'Product Details');
  R(f, 0, 100, 375, 250, C.bluePale);
  T(f, 147, 170, '💊', 80, 'Regular', C.blue);
  R(f, 20, 112, 68, 28, C.green, 6);
  T(f, 26, 118, '20% OFF', 11, 'Semi Bold', C.white);
  R(f, 321, 112, 34, 34, C.white, 17);
  T(f, 331, 118, '♡', 16, 'Regular', C.red);
  T(f, 20, 366, 'Paracetamol 500mg Tablet', 20, 'Bold', C.dark);
  T(f, 20, 394, 'by GSK Pharma  ·  10 Tablets', 14, 'Regular', C.gray);
  T(f, 20, 414, '★★★★☆   4.2   (342 reviews)', 12, 'Regular', C.amber);
  T(f, 20, 440, 'MRP: ₹40.00', 13, 'Regular', C.gray);
  T(f, 20, 460, '₹32.00', 28, 'Bold', C.blue);
  R(f, 120, 466, 70, 22, C.greenPale, 6);
  T(f, 126, 470, '✓ In Stock', 11, 'Semi Bold', C.green);
  ln(f, 20, 500, 335);
  T(f, 20, 510, 'Description', 15, 'Semi Bold', C.dark);
  T(f, 20, 532, 'Paracetamol relieves pain, fever and reduces inflammation.', 13, 'Regular', C.gray);
  T(f, 20, 558, 'Directions: Take 1-2 tablets every 4-6 hours as needed.', 13, 'Regular', C.gray);
  T(f, 20, 584, 'Quantity', 15, 'Semi Bold', C.dark);
  R(f, 20, 606, 38, 38, C.bluePale, 10);
  T(f, 31, 614, '−', 16, 'Bold', C.blue);
  T(f, 72, 612, '1', 18, 'Bold', C.dark);
  R(f, 98, 606, 38, 38, C.blue, 10);
  T(f, 109, 614, '+', 16, 'Bold', C.white);
  ln(f, 20, 658, 335);
  R(f, 20, 666, 163, 52, C.bluePale, 14);
  T(f, 40, 682, 'Add to Cart', 15, 'Semi Bold', C.blue);
  R(f, 193, 666, 162, 52, C.blue, 14);
  T(f, 217, 682, 'Buy Now', 15, 'Semi Bold', C.white);
  return f;
}

function C07_Cart() {
  var f = screen('C07 · Shopping Cart');
  statusBar(f);
  topBar(f, 'My Cart (3)');
  var items = [
    ['Paracetamol 500mg','10 Tabs','₹32.00'],
    ['Crocin 650mg','5 Tabs','₹45.00'],
    ['Vitamin C 500mg','30 Tabs','₹80.00'],
  ];
  items.forEach(function(item, i) {
    var y = 116 + i * 94;
    cardBox(f, 20, y, 335, 86);
    R(f, 30, y+10, 66, 66, C.bluePale, 10);
    T(f, 42, y+24, '💊', 24, 'Regular', C.blue);
    T(f, 108, y+12, item[0], 14, 'Semi Bold', C.dark);
    T(f, 108, y+32, item[1], 12, 'Regular', C.gray);
    R(f, 108, y+54, 28, 24, C.bluePale, 8);
    T(f, 117, y+57, '−', 14, 'Bold', C.blue);
    T(f, 144, y+57, '1', 14, 'Bold', C.dark);
    R(f, 160, y+54, 28, 24, C.blue, 8);
    T(f, 169, y+57, '+', 14, 'Bold', C.white);
    T(f, 287, y+14, item[2], 15, 'Bold', C.blue);
    T(f, 329, y+14, '🗑', 16, 'Regular', C.red);
  });
  R(f, 20, 406, 335, 50, C.white, 12, { stroke: C.lgray, sw: 0.5 });
  T(f, 36, 420, '🏷  Enter coupon code', 14, 'Regular', C.gray);
  T(f, 307, 422, 'Apply', 13, 'Semi Bold', C.blue);
  T(f, 20, 472, 'Price Summary', 16, 'Semi Bold', C.dark);
  var rows = [['Subtotal','₹157.00'],['Discount (20%)','−₹31.40'],['Delivery','Free']];
  rows.forEach(function(row, i) {
    T(f, 20, 502+i*28, row[0], 14, 'Regular', C.gray);
    T(f, 295, 502+i*28, row[1], 14, 'Regular', i===1 ? C.green : C.gray);
  });
  ln(f, 20, 590, 335);
  T(f, 20, 598, 'Total', 14, 'Semi Bold', C.dark);
  T(f, 287, 598, '₹125.60', 15, 'Bold', C.blue);
  R(f, 20, 668, 335, 50, C.blue, 14);
  T(f, 84, 684, 'Proceed to Checkout →', 15, 'Semi Bold', C.white);
  return f;
}

function C08_Prescription() {
  var f = screen('C08 · Upload Prescription');
  statusBar(f);
  topBar(f, 'Upload Prescription');
  R(f, 20, 116, 335, 62, C.bluePale, 14);
  T(f, 34, 128, "ℹ️  Upload a clear image of doctor's prescription for verification", 12, 'Regular', C.blue);
  var ua = figma.createRectangle();
  ua.x = 20; ua.y = 198; ua.resize(335, 200);
  ua.fills = [{ type: 'SOLID', color: C.white }];
  ua.strokes = [{ type: 'SOLID', color: C.blue }];
  ua.strokeWeight = 2; ua.dashPattern = [8, 4]; ua.cornerRadius = 18;
  f.appendChild(ua);
  T(f, 163, 244, '☁', 50, 'Regular', C.blue);
  T(f, 130, 312, 'Choose Image', 17, 'Semi Bold', C.dark);
  T(f, 88, 338, 'JPG, PNG, PDF  ·  Max 5MB', 14, 'Regular', C.gray);
  R(f, 20, 418, 163, 52, C.blue, 14);
  T(f, 46, 434, '📷  Camera', 15, 'Semi Bold', C.white);
  R(f, 194, 418, 161, 52, C.bluePale, 14);
  T(f, 210, 434, '🖼  Gallery', 15, 'Semi Bold', C.blue);
  T(f, 20, 490, 'Notes (Optional)', 15, 'Semi Bold', C.dark);
  R(f, 20, 516, 335, 80, C.white, 12, { stroke: C.lgray, sw: 1 });
  T(f, 34, 532, 'Add any specific instructions…', 14, 'Regular', C.gray);
  R(f, 20, 720, 335, 50, C.blue, 14);
  T(f, 90, 736, 'Submit Prescription', 15, 'Semi Bold', C.white);
  return f;
}

function C09_OrderPlaced() {
  var f = screen('C09 · Order Placed');
  statusBar(f);
  R(f, 87.5, 116, 200, 200, C.greenPale, 100);
  T(f, 152, 180, '✓', 80, 'Bold', C.green);
  T(f, 20, 340, 'Order Placed', 26, 'Bold', C.dark, 'CENTER');
  T(f, 20, 376, 'Successfully! 🎉', 26, 'Bold', C.dark, 'CENTER');
  R(f, 127.5, 434, 120, 32, C.bluePale, 10);
  T(f, 149, 443, '#OD123456', 14, 'Bold', C.blue);
  T(f, 20, 486, 'We will notify you once the pharmacy confirms', 14, 'Regular', C.gray, 'CENTER');
  R(f, 20, 544, 335, 50, C.blue, 14);
  T(f, 136, 560, 'Track Order', 15, 'Semi Bold', C.white);
  outlineBtn(f, 20, 608, 335, 'Continue Shopping');
  return f;
}

function C10_Tracking() {
  var f = screen('C10 · Order Tracking');
  statusBar(f);
  topBar(f, 'Track Order');
  T(f, 20, 116, 'Order #OD123456', 15, 'Semi Bold', C.dark);
  T(f, 20, 138, 'Placed on 10 May 2024, 10:30 AM', 12, 'Regular', C.gray);
  R(f, 20, 164, 335, 172, { r:0.851,g:0.921,b:0.949 }, 16);
  T(f, 108, 230, '🗺  Live Tracking Map', 15, 'Semi Bold', C.mid);
  T(f, 177, 264, '📍', 22, 'Regular', C.blue);
  var steps = [
    ['Order Received','10 May, 10:30 AM',true],
    ['Pharmacy Accepted','10 May, 11:00 AM',true],
    ['Preparing Your Order','10 May, 12:00 PM',true],
    ['Out for Delivery','10 May, 3:00 PM',false],
    ['Delivered','Expected by 5:00 PM',false],
  ];
  steps.forEach(function(step, i) {
    var y = 356 + i * 74;
    R(f, 20, y, 22, 22, step[2] ? C.green : C.white, 11, step[2] ? {} : {stroke:C.lgray,sw:1.5});
    if (step[2]) T(f, 25, y+3, '✓', 12, 'Bold', C.white);
    if (i < steps.length-1) R(f, 30, y+22, 2, 52, step[2] ? C.green : C.lgray);
    T(f, 56, y+2, step[0], 14, step[2] ? 'Semi Bold' : 'Regular', step[2] ? C.dark : C.gray);
    T(f, 56, y+22, step[1], 11, 'Regular', C.gray);
  });
  return f;
}

function C11_OrderHistory() {
  var f = screen('C11 · Order History');
  statusBar(f);
  topBar(f, 'My Orders');
  var tabDef = [[20,'Ongoing',false],[130,'Completed',true],[240,'Cancelled',false]];
  tabDef.forEach(function(td) {
    R(f, td[0], 100, 100, 36, td[2] ? C.blue : C.white, 18, td[2] ? {} : {stroke:C.lgray,sw:1});
    T(f, td[0]+10, 110, td[1], 13, td[2] ? 'Semi Bold' : 'Regular', td[2] ? C.white : C.gray);
  });
  var orders = [
    ['#OD123456','10 May 2024','3 items','₹162.80','Delivered',C.green,C.greenPale],
    ['#OD123455','05 May 2024','2 items','₹460.00','Delivered',C.green,C.greenPale],
    ['#OD123453','28 Apr 2024','5 items','₹230.00','Cancelled',C.red,C.redPale],
  ];
  orders.forEach(function(o, i) {
    var y = 150 + i * 108;
    cardBox(f, 20, y, 335, 100);
    T(f, 34, y+12, o[0], 14, 'Semi Bold', C.dark);
    T(f, 34, y+32, o[1], 12, 'Regular', C.gray);
    T(f, 34, y+50, o[2], 12, 'Regular', C.gray);
    T(f, 278, y+12, o[3], 15, 'Bold', C.blue);
    R(f, 280, y+34, 70, 22, o[6], 6);
    T(f, 290, y+38, o[4], 11, 'Semi Bold', o[5]);
    R(f, 34, y+70, 92, 24, C.bluePale, 6);
    T(f, 42, y+74, 'Repeat Order', 11, 'Semi Bold', C.blue);
  });
  bottomNav(f, 3);
  return f;
}

function C12_Profile() {
  var f = screen('C12 · Profile & Settings');
  statusBar(f, true);
  R(f, 0, 0, 375, 248, C.blue);
  R(f, 137.5, 62, 100, 100, C.blueMid, 50);
  T(f, 174, 100, 'SG', 22, 'Bold', C.white);
  T(f, 110, 178, 'Sachin Getnare', 18, 'Bold', C.white);
  T(f, 126, 204, '+91 88922 12921', 14, 'Regular', C.blueLight);
  var menus = [
    ['📍','My Addresses',false],['💊','My Prescriptions',false],
    ['💳','Payment Methods',false],['📦','Order History',false],
    ['🔔','Notifications',false],['❓','Help & Support',false],
    ['⚙','Settings',false],['🚪','Logout',true],
  ];
  menus.forEach(function(m, i) {
    var y = 264 + i * 57;
    R(f, 20, y, 335, 50, C.white, 12, {stroke:C.lgray,sw:0.5});
    T(f, 34, y+14, m[0], 20, 'Regular', m[2] ? C.red : C.blue);
    T(f, 70, y+16, m[1], 14, 'Regular', m[2] ? C.red : C.dark);
    T(f, 339, y+16, '›', 20, 'Regular', C.gray);
  });
  bottomNav(f, 4);
  return f;
}

// ═══════════════════════════════════════════════════════════════
// PHARMACY APP — 13 SCREENS
// ═══════════════════════════════════════════════════════════════

function P01_PharmLogin() {
  var f = screen('P01 · Pharmacy Login');
  statusBar(f);
  R(f, 20, 56, 60, 60, C.bluePale, 16);
  R(f, 48, 68, 4, 36, C.blue, 2);
  R(f, 34, 82, 32, 4, C.blue, 2);
  T(f, 92, 62, 'Pharmacy Login', 20, 'Bold', C.dark);
  T(f, 92, 90, 'Login to your account', 14, 'Regular', C.gray);
  R(f, 20, 138, 148, 72, C.bluePale, 12);
  T(f, 34, 150, 'New Orders', 12, 'Regular', C.gray);
  T(f, 34, 172, '12', 28, 'Bold', C.blue);
  R(f, 186, 138, 148, 72, C.greenPale, 12);
  T(f, 200, 150, 'Pending', 12, 'Regular', C.gray);
  T(f, 200, 172, '5', 28, 'Bold', C.green);
  R(f, 20, 226, 148, 72, C.amberPale, 12);
  T(f, 34, 238, 'Preparing', 12, 'Regular', C.gray);
  T(f, 34, 260, '7', 28, 'Bold', C.amber);
  R(f, 186, 226, 148, 72, C.xlight, 12);
  T(f, 200, 238, 'Completed', 12, 'Regular', C.gray);
  T(f, 200, 260, '24', 28, 'Bold', C.gray);
  inputField(f, 20, 318, 'Enter store name');
  inputField(f, 20, 382, 'Enter mobile number');
  inputField(f, 20, 446, 'Password');
  T(f, 232, 510, 'Forgot Password?', 13, 'Semi Bold', C.blue);
  primaryBtn(f, 20, 542, 335, 'Login');
  R(f, 20, 608, 18, 18, C.white, 4, {stroke:C.lgray,sw:1.5});
  T(f, 44, 608, 'Remember Me', 14, 'Regular', C.gray);
  return f;
}

function P02_Dashboard() {
  var f = screen('P02 · Dashboard');
  statusBar(f);
  R(f, 0, 44, 375, 78, C.white);
  ln(f, 0, 121, 375);
  T(f, 20, 58, 'Hello, Pharmacy 👋', 16, 'Semi Bold', C.dark);
  T(f, 20, 80, 'Good Morning', 13, 'Regular', C.gray);
  T(f, 244, 66, '19 May 2024', 12, 'Regular', C.gray);
  R(f, 20, 136, 335, 74, C.blue, 16);
  T(f, 34, 148, "Today's Revenue", 13, 'Regular', C.blueLight);
  T(f, 34, 170, '₹18,650', 24, 'Bold', C.white);
  R(f, 255, 156, 84, 30, C.blueMid, 8);
  T(f, 263, 163, 'View Details', 12, 'Semi Bold', C.white);
  var statsGrid = [
    ['New Orders','12',C.bluePale,C.blue],
    ['Preparing','7',C.greenPale,C.green],
    ['Pending','5',C.amberPale,C.amber],
    ['Completed','24',C.xlight,C.gray],
  ];
  statsGrid.forEach(function(s, i) {
    var gx = 20 + (i%2)*177, gy = 228 + Math.floor(i/2)*86;
    R(f, gx, gy, 158, 74, s[2], 12);
    T(f, gx+14, gy+12, s[0], 12, 'Regular', C.gray);
    T(f, gx+14, gy+36, s[1], 22, 'Bold', s[3]);
  });
  T(f, 20, 414, 'Recent Orders', 16, 'Semi Bold', C.dark);
  var recOrders = [
    ['#OD123456','Sachin Getnare','4 items','₹112.80','New',C.blue,C.bluePale],
    ['#OD123455','Rahul Sharma','2 items · Rx','₹460.00','Ongoing',C.amber,C.amberPale],
    ['#OD123454','Neha Patil','5 items · Rx','₹113 Pend','Prep',C.green,C.greenPale],
  ];
  recOrders.forEach(function(o, i) {
    var ry = 442 + i * 80;
    R(f, 20, ry, 335, 72, C.white, 12, {stroke:C.lgray,sw:0.5});
    T(f, 34, ry+10, o[0], 13, 'Semi Bold', C.dark);
    T(f, 34, ry+28, o[1], 12, 'Regular', C.gray);
    T(f, 34, ry+46, o[2], 11, 'Regular', C.gray);
    T(f, 256, ry+10, o[3], 13, 'Bold', C.blue);
    R(f, 256, ry+30, 66, 20, o[6], 6);
    T(f, 264, ry+33, o[4], 11, 'Semi Bold', o[5]);
    R(f, 256, ry+54, 50, 20, C.blue, 6);
    T(f, 264, ry+57, 'Accept', 11, 'Semi Bold', C.white);
    R(f, 312, ry+54, 42, 20, C.xlight, 6);
    T(f, 318, ry+57, 'Reject', 11, 'Regular', C.gray);
  });
  pharmNav(f, 0);
  return f;
}

function P03_NewOrders() {
  var f = screen('P03 · New Orders');
  statusBar(f);
  topBar(f, 'New Orders (12)');
  var chips = ['All','New','Prep','Ready','Done'];
  chips.forEach(function(chip, i) {
    R(f, 20+i*68, 108, 62, 28, i===0?C.blue:C.white, 14, i>0?{stroke:C.lgray,sw:1}:{});
    T(f, 28+i*68, 115, chip, 12, i===0?'Semi Bold':'Regular', i===0?C.white:C.gray);
  });
  var orders = [
    ['#OD123456','Sachin Getnare','10:38 AM','4 items · Prescription','₹112.80','New',C.blue,C.bluePale],
    ['#OD123455','Rahul Sharma','Only 41 mins','2 items · Rx Required','₹460.00','Prep',C.amber,C.amberPale],
    ['#OD123454','Neha Patil','09:19 AM','5 items · Prescription','₹230.00','Ready',C.green,C.greenPale],
  ];
  orders.forEach(function(o, i) {
    var oy = 150 + i * 104;
    cardBox(f, 20, oy, 335, 96);
    T(f, 34, oy+10, o[0], 13, 'Semi Bold', C.dark);
    T(f, 238, oy+10, o[2], 12, 'Regular', C.gray);
    T(f, 34, oy+30, o[1], 13, 'Regular', C.dark);
    T(f, 34, oy+50, o[3], 12, 'Regular', C.gray);
    T(f, 256, oy+30, o[4], 14, 'Bold', C.blue);
    R(f, 256, oy+50, 66, 20, o[7], 6);
    T(f, 264, oy+53, o[5], 11, 'Semi Bold', o[6]);
    R(f, 34, oy+70, 66, 22, C.green, 8);
    T(f, 42, oy+73, 'Accept', 12, 'Semi Bold', C.white);
    R(f, 108, oy+70, 56, 22, C.xlight, 8);
    T(f, 116, oy+73, 'Reject', 12, 'Regular', C.gray);
  });
  return f;
}

function P04_OrderDetail() {
  var f = screen('P04 · Order Details');
  statusBar(f);
  topBar(f, 'Order #OD123456');
  R(f, 20, 116, 335, 68, C.bluePale, 12);
  T(f, 34, 128, 'Sachin Getnare', 15, 'Semi Bold', C.dark);
  T(f, 34, 150, '+91 88922 13621', 13, 'Regular', C.gray);
  T(f, 270, 138, '📞 Call', 13, 'Semi Bold', C.blue);
  T(f, 20, 200, 'Delivery Address', 14, 'Semi Bold', C.dark);
  T(f, 20, 220, '📍 Wardha Road, Nagpur - 440001', 13, 'Regular', C.gray);
  T(f, 20, 252, 'Order Items', 14, 'Semi Bold', C.dark);
  var oi = [['Paracetamol 500mg','x2','₹64.00'],['Crocin 650mg','x1','₹45.75'],['Vitamin C 500mg','x1','₹80.00']];
  oi.forEach(function(item, i) {
    T(f, 20, 276+i*44, item[0], 14, 'Regular', C.dark);
    T(f, 246, 276+i*44, item[1], 14, 'Regular', C.gray);
    T(f, 300, 276+i*44, item[2], 14, 'Semi Bold', C.blue);
    ln(f, 20, 298+i*44, 335);
  });
  T(f, 20, 414, 'Order Total', 15, 'Semi Bold', C.dark);
  T(f, 270, 416, '₹189.75', 15, 'Bold', C.blue);
  R(f, 20, 452, 335, 110, C.bluePale, 12);
  T(f, 34, 466, '📋 Prescription', 14, 'Semi Bold', C.dark);
  T(f, 34, 488, 'Uploaded on 10 May, 10:30 AM', 12, 'Regular', C.gray);
  T(f, 34, 506, 'Please deliver fast', 12, 'Regular', C.gray);
  R(f, 240, 462, 98, 72, C.xlight, 10);
  T(f, 275, 490, '📄', 24, 'Regular', C.gray);
  R(f, 20, 582, 140, 50, C.xlight, 14);
  T(f, 58, 598, 'Reject', 15, 'Semi Bold', C.gray);
  R(f, 175, 582, 180, 50, C.blue, 14);
  T(f, 221, 598, 'Accept', 15, 'Semi Bold', C.white);
  return f;
}

function P05_RxReview() {
  var f = screen('P05 · Prescription Review');
  statusBar(f);
  topBar(f, 'Prescription Review');
  R(f, 20, 116, 335, 260, C.xlight, 16);
  T(f, 80, 202, 'Rx Prescription Image', 18, 'Semi Bold', C.gray);
  T(f, 120, 234, 'Review…', 20, 'Regular', C.mid);
  T(f, 155, 268, '📋', 30, 'Regular', C.gray);
  T(f, 20, 394, 'Verify Items:', 15, 'Semi Bold', C.dark);
  var rxItems = ['Paracetamol 500mg','Crocin 650mg','Vitamin C Advance'];
  rxItems.forEach(function(item, i) {
    R(f, 20, 418+i*38, 20, 20, C.green, 10);
    T(f, 25, 420+i*38, '✓', 12, 'Bold', C.white);
    T(f, 50, 420+i*38, item, 14, 'Regular', C.dark);
  });
  R(f, 20, 548, 140, 50, C.xlight, 14);
  T(f, 56, 564, 'Zoom', 15, 'Semi Bold', C.gray);
  R(f, 175, 548, 180, 50, C.blue, 14);
  T(f, 209, 564, 'Download', 15, 'Semi Bold', C.white);
  return f;
}

function P06_PrepareOrder() {
  var f = screen('P06 · Prepare Order');
  statusBar(f);
  topBar(f, 'Prepare Order');
  T(f, 20, 116, 'Items to Prepare', 16, 'Semi Bold', C.dark);
  var prItems = [
    ['Paracetamol 500mg','2 Tablets',true],
    ['Crocin 650mg','1 Tablet',true],
    ['Vitamin C 500mg','1 Tablet',true],
    ['Crocin Advance','2 Tablets',false],
  ];
  prItems.forEach(function(item, i) {
    var iy = 148 + i * 64;
    R(f, 20, iy, 335, 56, C.white, 12, {stroke:item[2]?C.green:C.lgray, sw:item[2]?2:0.5});
    R(f, 30, iy+17, 22, 22, item[2]?C.green:C.xlight, 11);
    if (item[2]) T(f, 35, iy+19, '✓', 12, 'Bold', C.white);
    T(f, 64, iy+10, item[0], 14, 'Semi Bold', C.dark);
    T(f, 64, iy+30, item[1], 13, 'Regular', C.gray);
    T(f, 298, iy+17, item[2]?'Ready':'Pending', 12, 'Semi Bold', item[2]?C.green:C.amber);
  });
  R(f, 20, 426, 335, 50, C.blue, 14);
  T(f, 98, 442, 'Mark as Packed', 15, 'Semi Bold', C.white);
  return f;
}

function P07_GenerateBill() {
  var f = screen('P07 · Generate Bill');
  statusBar(f);
  topBar(f, 'Bill Summary');
  R(f, 20, 116, 335, 48, C.bluePale, 12);
  T(f, 34, 130, '🧾 Bill Summary — Order #OD123456', 14, 'Semi Bold', C.blue);
  var billItems = [['Paracetamol 500mg x 2','₹64.00'],['Crocin 650mg x 1','₹45.75'],['Vitamin C 500mg x 1','₹60.00']];
  billItems.forEach(function(item, i) {
    T(f, 20, 184+i*44, item[0], 14, 'Regular', C.dark);
    T(f, 300, 184+i*44, item[1], 14, 'Bold', C.blue);
    ln(f, 20, 206+i*44, 335);
  });
  var summary = [['Subtotal','₹169.75'],['Discount (20%)','−₹33.95'],['Delivery Charges','₹20.00']];
  summary.forEach(function(s, i) {
    T(f, 20, 322+i*28, s[0], 14, 'Regular', C.gray);
    T(f, 295, 322+i*28, s[1], 14, 'Regular', i===1?C.green:C.gray);
  });
  ln(f, 20, 406, 335);
  T(f, 20, 414, 'Total Amount', 16, 'Semi Bold', C.dark);
  T(f, 264, 414, '₹169.60', 16, 'Bold', C.blue);
  R(f, 20, 468, 335, 50, C.blue, 14);
  T(f, 114, 484, 'Generate Bill', 15, 'Semi Bold', C.white);
  return f;
}

function P08_UpdateStatus() {
  var f = screen('P08 · Update Order Status');
  statusBar(f);
  topBar(f, 'Order #OD123456');
  T(f, 20, 116, 'Current Status', 14, 'Regular', C.gray);
  T(f, 20, 138, 'Preparing Your Order', 16, 'Semi Bold', C.dark);
  ln(f, 20, 166, 335);
  T(f, 20, 176, 'Update Status', 16, 'Semi Bold', C.dark);
  var statuses = [['Accepted',true],['Preparing',true],['Ready for Pickup',false],['Out for Delivery',false],['Delivered',false],['Cancelled',false]];
  statuses.forEach(function(s, i) {
    R(f, 20, 206+i*58, 335, 48, s[1]?C.bluePale:C.white, 12, s[1]?{}:{stroke:C.lgray,sw:0.5});
    R(f, 297, 206+i*58+13, 22, 22, s[1]?C.blue:C.white, 11, s[1]?{}:{stroke:C.lgray,sw:1});
    if (s[1]) T(f, 302, 206+i*58+15, '●', 12, 'Regular', C.white);
    T(f, 36, 206+i*58+15, s[0], 14, s[1]?'Semi Bold':'Regular', s[1]?C.blue:C.dark);
  });
  R(f, 20, 562, 335, 50, C.blue, 14);
  T(f, 106, 578, 'Update Status', 15, 'Semi Bold', C.white);
  return f;
}

function P09_Inventory() {
  var f = screen('P09 · Inventory / Products');
  statusBar(f);
  topBar(f, 'Products');
  R(f, 20, 116, 248, 40, C.white, 20, {stroke:C.lgray,sw:1});
  T(f, 34, 126, '🔍 Search products', 13, 'Regular', C.gray);
  R(f, 284, 116, 71, 40, C.blue, 10);
  T(f, 295, 126, '+ Add', 13, 'Semi Bold', C.white);
  R(f, 20, 172, 158, 62, C.bluePale, 12);
  T(f, 34, 182, 'Total Products', 12, 'Regular', C.gray);
  T(f, 34, 204, '48', 22, 'Bold', C.blue);
  R(f, 194, 172, 161, 62, C.amberPale, 12);
  T(f, 208, 182, 'Total Revenue', 12, 'Regular', C.gray);
  T(f, 208, 204, '₹18,650', 18, 'Bold', C.amber);
  var prods = [
    ['Paracetamol 500mg','In Stock: 80',C.green],
    ['Crocin 650mg','In Stock: 30',C.green],
    ['Vitamin C 500mg','In Stock: 12',C.amber],
    ['Zinocef Tablet','In Stock: 5  ⚠',C.red],
  ];
  prods.forEach(function(p, i) {
    cardBox(f, 20, 250+i*78, 335, 70);
    R(f, 30, 260+i*78, 44, 44, C.bluePale, 10);
    T(f, 42, 272+i*78, '💊', 22, 'Regular', C.blue);
    T(f, 86, 262+i*78, p[0], 14, 'Semi Bold', C.dark);
    T(f, 86, 282+i*78, p[1], 12, 'Regular', p[2]);
    R(f, 273, 268+i*78, 60, 26, C.blue, 8);
    T(f, 281, 273+i*78, 'Edit', 13, 'Semi Bold', C.white);
  });
  R(f, 20, 574, 335, 44, C.blue, 14);
  T(f, 100, 590, '+ Add New Product', 15, 'Semi Bold', C.white);
  pharmNav(f, 2);
  return f;
}

function P10_Reports() {
  var f = screen('P10 · Reports');
  statusBar(f);
  topBar(f, 'Reports');
  T(f, 20, 116, 'Today  •  19 May 2024', 16, 'Semi Bold', C.dark);
  R(f, 20, 142, 155, 80, C.bluePale, 12);
  T(f, 34, 154, 'Total Orders', 12, 'Regular', C.gray);
  T(f, 34, 180, '48', 28, 'Bold', C.blue);
  R(f, 192, 142, 163, 80, C.greenPale, 12);
  T(f, 206, 154, 'Total Revenue', 12, 'Regular', C.gray);
  T(f, 206, 180, '₹18,650', 22, 'Bold', C.green);
  R(f, 20, 238, 335, 160, C.xlight, 14);
  T(f, 110, 300, '📊 Revenue Chart', 16, 'Semi Bold', C.gray);
  var bars = [40,60,50,80,70,90,65];
  bars.forEach(function(h, i) {
    R(f, 40+i*44, 392-h, 30, h, C.blue, 4, {opacity:0.55+i*0.05});
  });
  T(f, 20, 414, 'Top Selling Products', 16, 'Semi Bold', C.dark);
  ['1.  Paracetamol 500mg','2.  Crocin 650mg','3.  Vitamin C 500mg'].forEach(function(item, i) {
    T(f, 20, 442+i*26, item, 14, 'Regular', C.dark);
  });
  R(f, 20, 554, 335, 130, C.xlight, 12);
  T(f, 34, 568, 'MedPlus Pharmacy', 16, 'Semi Bold', C.dark);
  T(f, 34, 592, 'Nagpur, Maharashtra', 13, 'Regular', C.gray);
  T(f, 34, 612, '📞 +91 88623 43210', 13, 'Regular', C.gray);
  T(f, 34, 632, '📍 Wardha Road, Nagpur - 440001', 13, 'Regular', C.gray);
  T(f, 220, 568, '5 May 2024', 12, 'Regular', C.gray);
  return f;
}

function P11_PharmProfile() {
  var f = screen('P11 · Pharmacy Profile');
  statusBar(f);
  topBar(f, 'Pharmacy Profile');
  R(f, 117.5, 116, 140, 140, C.bluePale, 70);
  T(f, 155.5, 160, '🏥', 60, 'Regular', C.blue);
  T(f, 50, 270, 'MedPlus Pharmacy', 18, 'Bold', C.dark, 'CENTER');
  T(f, 80, 298, 'Nagpur, Maharashtra', 14, 'Regular', C.gray, 'CENTER');
  var pInfo = [
    ['📞','Phone','+91 88623 43210'],
    ['📧','Email','medplus@pharmacy.com'],
    ['📍','Address','Wardha Road, Nagpur - 440001'],
    ['🏪','License','PH/MH/2021/12345'],
    ['⏰','Hours','9:00 AM – 9:00 PM'],
  ];
  pInfo.forEach(function(info, i) {
    R(f, 20, 330+i*66, 335, 58, C.white, 12, {stroke:C.lgray,sw:0.5});
    T(f, 30, 330+i*66+18, info[0], 20, 'Regular', C.blue);
    T(f, 64, 330+i*66+10, info[1], 12, 'Regular', C.gray);
    T(f, 64, 330+i*66+28, info[2], 13, 'Regular', C.dark);
  });
  R(f, 20, 668, 335, 50, C.blue, 14);
  T(f, 124, 684, 'Edit Profile', 15, 'Semi Bold', C.white);
  pharmNav(f, 3);
  return f;
}

function P12_Notifications() {
  var f = screen('P12 · Notifications');
  statusBar(f);
  topBar(f, 'Notifications', 'Mark All Read');
  var notifs = [
    ['🔔','New Order Received','Order #OD123456','10:38 AM',C.bluePale,true],
    ['✅','Order Accepted','Order #OD123455','Yesterday',C.greenPale,false],
    ['🚚','Order Delivered','Order #OD123452','Yesterday',C.greenPale,false],
    ['⚠️','Low Stock Alert','Paracetamol 500mg','Yesterday',C.amberPale,false],
    ['💰','Payment Received','₹148.60 · 5 May 2024','5 May',C.xlight,false],
  ];
  notifs.forEach(function(n, i) {
    var ny = 116 + i * 100;
    R(f, 20, ny, 335, 88, n[4], 12);
    if (n[5]) R(f, 14, ny+33, 6, 22, C.blue, 3);
    R(f, 30, ny+12, 40, 40, C.white, 20);
    T(f, 36, ny+18, n[0], 22, 'Regular', C.blue);
    T(f, 82, ny+14, n[1], 14, 'Semi Bold', C.dark);
    T(f, 82, ny+34, n[2], 12, 'Regular', C.gray);
    T(f, 274, ny+14, n[3], 11, 'Regular', C.gray);
    if (n[5]) { R(f, 82, ny+56, 46, 20, C.blue, 6); T(f, 88, ny+59, 'New', 11, 'Semi Bold', C.white); }
  });
  R(f, 20, 626, 335, 44, C.bluePale, 10);
  T(f, 84, 640, 'View All Notifications', 15, 'Semi Bold', C.blue);
  return f;
}

function P13_Settings() {
  var f = screen('P13 · Settings');
  statusBar(f);
  topBar(f, 'Settings');
  var settingsItems = [
    ['🔔','Push Notifications',false],['📱','SMS Alerts',false],
    ['🔐','Change Password',false],['🌐','Language',false],
    ['📊','Data & Privacy',false],['ℹ️','About App',false],
    ['🚪','Logout',true],
  ];
  settingsItems.forEach(function(s, i) {
    R(f, 20, 116+i*66, 335, 58, C.white, 12, {stroke:C.lgray,sw:0.5});
    T(f, 34, 116+i*66+18, s[0], 20, 'Regular', s[2]?C.red:C.blue);
    T(f, 70, 116+i*66+20, s[1], 15, 'Regular', s[2]?C.red:C.dark);
    if (!s[2]) T(f, 339, 116+i*66+18, '›', 20, 'Regular', C.gray);
    else { R(f, 293, 116+i*66+18, 42, 22, C.redPale, 6); T(f, 301, 116+i*66+21, 'Logout', 11, 'Semi Bold', C.red); }
  });
  return f;
}

// ═══════════════════════════════════════════════════════════════
// MAIN GENERATOR
// ═══════════════════════════════════════════════════════════════

async function generateAll() {
  function getOrCreatePage(name) {
    var page = figma.root.children.find(function(p) { return p.name === name; });
    if (!page) { page = figma.createPage(); page.name = name; }
    else { var kids = [...page.children]; kids.forEach(function(c) { c.remove(); }); }
    return page;
  }

  var custPage = getOrCreatePage('Customer App');
  var pharmPage = getOrCreatePage('Pharmacy App');

  // Build Customer screens
  figma.currentPage = custPage;
  var custScreens = [
    C01_Splash(), C02_Login(), C03_Home(), C04_Categories(),
    C05_Search(), C06_Product(), C07_Cart(), C08_Prescription(),
    C09_OrderPlaced(), C10_Tracking(), C11_OrderHistory(), C12_Profile(),
  ];
  custScreens.forEach(function(s, i) {
    s.x = i * 415; s.y = 0;
    custPage.appendChild(s);
  });

  // Build Pharmacy screens
  figma.currentPage = pharmPage;
  var pharmScreens = [
    P01_PharmLogin(), P02_Dashboard(), P03_NewOrders(), P04_OrderDetail(),
    P05_RxReview(), P06_PrepareOrder(), P07_GenerateBill(), P08_UpdateStatus(),
    P09_Inventory(), P10_Reports(), P11_PharmProfile(), P12_Notifications(), P13_Settings(),
  ];
  pharmScreens.forEach(function(s, i) {
    s.x = i * 415; s.y = 0;
    pharmPage.appendChild(s);
  });

  // Prototype links — Customer App (sequential + loop to home)
  figma.currentPage = custPage;
  for (var i = 0; i < custScreens.length - 1; i++) {
    addHotspot(custScreens[i], custScreens[i + 1]);
  }
  addHotspot(custScreens[custScreens.length - 1], custScreens[2]); // Profile → Home

  // Prototype links — Pharmacy App (sequential + loop to dashboard)
  figma.currentPage = pharmPage;
  for (var j = 0; j < pharmScreens.length - 1; j++) {
    addHotspot(pharmScreens[j], pharmScreens[j + 1]);
  }
  addHotspot(pharmScreens[pharmScreens.length - 1], pharmScreens[1]); // Settings → Dashboard

  figma.currentPage = custPage;
  figma.viewport.scrollAndZoomIntoView(custScreens);
  figma.notify('✅ DawaMart ready!  Customer App: 12 screens  |  Pharmacy App: 13 screens', { timeout: 5000 });
}
