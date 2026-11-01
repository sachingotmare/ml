figma.showUI(__html__, { width: 320, height: 660, title: 'IWM Wireframe Generator' });

figma.ui.onmessage = async function(msg) {
  if (msg.type === 'GENERATE') {
    try {
      await loadFonts();
      await generateScreens(msg.opts);
      figma.ui.postMessage({ type: 'DONE', text: 'All screens generated!' });
    } catch (e) {
      figma.notify('Error: ' + e.message, { error: true });
      figma.ui.postMessage({ type: 'ERROR', text: e.message });
    }
  }
  if (msg.type === 'ARRANGE') {
    try {
      await loadFonts();
      arrangeExisting(msg.opts);
      figma.ui.postMessage({ type: 'DONE', text: 'Frames arranged!' });
    } catch (e) {
      figma.ui.postMessage({ type: 'ERROR', text: e.message });
    }
  }
};

async function loadFonts() {
  await Promise.all([
    figma.loadFontAsync({ family: 'Inter', style: 'Regular' }),
    figma.loadFontAsync({ family: 'Inter', style: 'Medium' }),
    figma.loadFontAsync({ family: 'Inter', style: 'Semi Bold' }),
    figma.loadFontAsync({ family: 'Inter', style: 'Bold' }),
  ]);
}

var C = {
  primary:   { r:0.102, g:0.235, b:0.431 },
  primaryL:  { r:0.145, g:0.345, b:0.659 },
  secondary: { r:0.059, g:0.608, b:0.557 },
  accent:    { r:0.961, g:0.486, b:0.000 },
  success:   { r:0.180, g:0.490, b:0.196 },
  successL:  { r:0.831, g:0.929, b:0.831 },
  warning:   { r:0.980, g:0.659, b:0.145 },
  warningL:  { r:1.000, g:0.953, b:0.804 },
  danger:    { r:0.776, g:0.157, b:0.157 },
  dangerL:   { r:0.973, g:0.843, b:0.843 },
  info:      { r:0.009, g:0.467, b:0.741 },
  infoL:     { r:0.820, g:0.929, b:0.945 },
  purple:    { r:0.486, g:0.227, b:0.929 },
  purpleL:   { r:0.929, g:0.910, b:1.000 },
  bg:        { r:0.961, g:0.969, b:0.980 },
  surface:   { r:1.000, g:1.000, b:1.000 },
  sidebar:   { r:0.059, g:0.153, b:0.267 },
  text:      { r:0.110, g:0.110, b:0.118 },
  textMid:   { r:0.420, g:0.447, b:0.502 },
  border:    { r:0.898, g:0.906, b:0.918 },
  gray1:     { r:0.953, g:0.953, b:0.953 },
  tealL:     { r:0.800, g:0.984, b:0.945 },
  blueL:     { r:0.859, g:0.929, b:1.000 },
  white:     { r:1, g:1, b:1 },
  black:     { r:0, g:0, b:0 },
  sidebarTx: { r:0.800, g:0.840, b:0.900 },
  sidebarSb: { r:0.400, g:0.450, b:0.500 },
};

var SW = 220;
var NH = 56;

function R(parent, x, y, w, h, color, radius, stroke) {
  var r = figma.createRectangle();
  r.x = x; r.y = y;
  r.resize(Math.max(w, 1), Math.max(h, 1));
  r.fills = [{ type: 'SOLID', color: color }];
  if (radius) r.cornerRadius = radius;
  if (stroke) { r.strokes = [{ type: 'SOLID', color: stroke }]; r.strokeWeight = 1; r.strokeAlign = 'INSIDE'; }
  parent.appendChild(r);
  return r;
}

function T(parent, x, y, text, size, style, color, w) {
  var t = figma.createText();
  t.x = x; t.y = y;
  t.fontName = { family: 'Inter', style: style };
  t.fontSize = size;
  t.characters = String(text);
  t.fills = [{ type: 'SOLID', color: color }];
  if (w) { t.textAutoResize = 'HEIGHT'; t.resize(w, 20); }
  parent.appendChild(t);
  return t;
}

function E(parent, x, y, w, h, color) {
  var e = figma.createEllipse();
  e.x = x; e.y = y; e.resize(w, h);
  e.fills = [{ type: 'SOLID', color: color }];
  parent.appendChild(e);
  return e;
}

function F(name, w, h, color) {
  var f = figma.createFrame();
  f.name = name; f.resize(w, h);
  f.fills = [{ type: 'SOLID', color: color || C.bg }];
  f.clipsContent = true;
  return f;
}

function LN(parent, x, y, w) { R(parent, x, y, w, 1, C.border); }

function badge(parent, x, y, text, bg, fg, w) {
  w = w || 60;
  R(parent, x, y, w, 20, bg, 10);
  T(parent, x + 6, y + 3, text, 9, 'Semi Bold', fg);
}

function inp(parent, x, y, w, label, value) {
  if (label) T(parent, x, y, label, 11, 'Medium', C.textMid, w);
  var ty = label ? y + 18 : y;
  R(parent, x, ty, w, 36, C.surface, 4, C.border);
  T(parent, x + 10, ty + 10, value || '', 12, 'Regular', value ? C.text : C.textMid, w - 20);
}

function btn(parent, x, y, w, label, style) {
  var bg = style === 'danger' ? C.danger : style === 'success' ? C.success : style === 'outline' ? C.surface : style === 'secondary' ? C.gray1 : C.primary;
  var fg = (style === 'outline') ? C.primary : (style === 'secondary') ? C.text : C.white;
  R(parent, x, y, w, 36, bg, 4, style === 'outline' ? C.primary : null);
  T(parent, x + 10, y + 10, label, 12, 'Semi Bold', fg, w - 20);
}

function sidebar(f, h, active) {
  R(f, 0, 0, SW, h, C.sidebar);
  R(f, 0, 0, SW, 64, { r:0, g:0.05, b:0.12 });
  R(f, 14, 14, 36, 36, C.accent, 8);
  T(f, 20, 19, 'W', 18, 'Bold', C.white);
  T(f, 58, 16, 'IWM Portal', 13, 'Bold', C.white);
  T(f, 58, 33, 'Warehouse Mgmt', 10, 'Regular', C.sidebarTx);
  LN(f, 0, 64, SW);
  T(f, 14, 72, 'MAIN', 9, 'Bold', C.sidebarSb, SW - 28);
  T(f, 14, 178, 'OPERATIONS', 9, 'Bold', C.sidebarSb, SW - 28);
  T(f, 14, 278, 'ADMIN', 9, 'Bold', C.sidebarSb, SW - 28);
  var items = [
    { label: 'Dashboard',     y: 84,  key: 'dashboard' },
    { label: 'Products',      y: 116, key: 'products'  },
    { label: 'Categories',    y: 148, key: 'categories'},
    { label: 'Orders',        y: 190, key: 'orders',   bval: '12', bc: C.danger, bfc: C.white },
    { label: 'Prescriptions', y: 222, key: 'prescriptions', bval: '4', bc: C.danger, bfc: C.white },
    { label: 'Reports',       y: 290, key: 'reports'   },
    { label: 'Users',         y: 322, key: 'users'     },
    { label: 'Settings',      y: 354, key: 'settings'  },
  ];
  items.forEach(function(item) {
    var isA = item.key === active;
    if (isA) {
      R(f, 0, item.y - 2, 3, 34, C.accent);
      R(f, 0, item.y - 2, SW, 34, C.accent).opacity = 0.12;
    }
    T(f, 34, item.y + 6, item.label, 12.5, isA ? 'Semi Bold' : 'Regular', isA ? C.white : C.sidebarTx);
    if (item.bval) badge(f, SW - 42, item.y + 4, item.bval, item.bc, item.bfc, 28);
  });
  LN(f, 0, h - 60, SW);
  E(f, 14, h - 46, 32, 32, C.primaryL);
  T(f, 18, h - 40, 'SG', 11, 'Bold', C.white);
  T(f, 54, h - 46, 'Admin User', 12, 'Semi Bold', C.white);
  T(f, 54, h - 30, 'Administrator', 10, 'Regular', C.sidebarTx);
}

function topnav(f, W, title, sub) {
  R(f, SW, 0, W - SW, NH, C.surface, 0, C.border);
  T(f, SW + 18, sub ? 8 : 20, title, sub ? 11 : 14, 'Regular', C.textMid, W - SW - 200);
  if (sub) T(f, SW + 18, 26, sub, 15, 'Bold', C.text, W - SW - 200);
  R(f, W - 280, 12, 200, 32, C.bg, 16, C.border);
  T(f, W - 268, 20, 'Search...', 11, 'Regular', C.textMid);
  E(f, W - 30, 10, 32, 32, C.primary);
  T(f, W - 23, 17, 'SG', 10, 'Bold', C.white);
}

function statCard(f, x, y, w, icon, val, label, color, iconBg) {
  R(f, x, y, w, 96, C.surface, 8, C.border);
  R(f, x + 12, y + 12, 40, 40, iconBg, 8);
  T(f, x + 20, y + 20, icon, 16, 'Regular', color);
  T(f, x + 62, y + 12, val, 24, 'Bold', color);
  T(f, x + 62, y + 42, label, 10, 'Regular', C.textMid, w - 74);
}

function card(f, x, y, w, h, title) {
  R(f, x, y, w, h, C.surface, 8, C.border);
  if (title) {
    R(f, x, y, w, 44, C.gray1);
    LN(f, x, y + 44, w);
    T(f, x + 14, y + 14, title, 13, 'Semi Bold', C.text, w - 28);
  }
}

function tbl(f, x, y, w, headers, rows) {
  var cw = Math.floor(w / headers.length);
  R(f, x, y, w, 36, C.gray1);
  LN(f, x, y + 36, w);
  headers.forEach(function(h, i) {
    T(f, x + cw * i + 10, y + 11, h.toUpperCase(), 9, 'Bold', C.textMid, cw - 20);
  });
  rows.forEach(function(row, ri) {
    var ry = y + 36 + ri * 44;
    R(f, x, ry, w, 44, ri % 2 === 0 ? C.surface : C.gray1);
    LN(f, x, ry + 44, w);
    row.forEach(function(cell, ci) {
      T(f, x + cw * ci + 10, ry + 14, String(cell), 11, 'Regular', C.text, cw - 20);
    });
  });
}

// ── SCREENS ──────────────────────────────────────────────────

function buildLogin(W) {
  var f = F('01_Login', W, 820, C.bg);
  var HW = Math.floor(W / 2);
  R(f, 0, 0, HW, 820, C.primary);
  R(f, 0, 0, HW, 820, C.secondary).opacity = 0.2;
  R(f, 14, 14, 36, 36, C.accent, 8);
  T(f, 20, 19, 'W', 18, 'Bold', C.white);
  T(f, 58, 16, 'IWM Portal', 13, 'Bold', C.white);
  T(f, 56, 160, 'Simplifying Warehouse', 28, 'Bold', C.white, HW - 112);
  T(f, 56, 196, 'Operations', 28, 'Bold', C.white, HW - 112);
  T(f, 56, 244, 'Manage orders, inventory and\nprescriptions from one platform.', 13, 'Regular', { r:0.85, g:0.9, b:0.95 }, HW - 112);
  ['Order & Inventory Mgmt', 'Prescription Upload & Review', 'Real-time Dashboard & Reports', 'Role-based Access Control'].forEach(function(ft, i) {
    T(f, 56, 320 + i * 30, ft, 12, 'Regular', { r:0.9, g:0.92, b:0.95 }, HW - 112);
  });
  var fx = HW + 80, fw = W - HW - 160;
  T(f, fx, 110, 'Welcome Back', 28, 'Bold', C.text);
  T(f, fx, 148, 'Login to your Warehouse Management account', 12, 'Regular', C.textMid, fw);
  inp(f, fx, 196, fw, 'Email / Username *', 'admin@warehouse.com');
  inp(f, fx, 270, fw, 'Password *', '••••••••');
  T(f, fx, 332, 'Remember me', 12, 'Regular', C.textMid);
  T(f, fx + fw - 100, 332, 'Forgot Password?', 12, 'Semi Bold', C.primary);
  btn(f, fx, 360, fw, 'Login to Dashboard', 'primary');
  T(f, fx + 20, 418, 'Powered by SG Softech | support@sgsoftech.in', 11, 'Regular', C.textMid, fw);
  return f;
}

function buildDashboard(W) {
  var H = 1020; var f = F('03_Dashboard', W, H, C.bg);
  var CW = W - SW;
  sidebar(f, H, 'dashboard');
  topnav(f, W, 'Dashboard', 'Welcome back, Admin');
  var cx = SW + 20, cy = NH + 20;
  T(f, cx, cy, 'Dashboard', 20, 'Bold', C.text);
  btn(f, W - 220, cy, 140, '+ New Order', 'primary');
  var cardW = Math.floor((CW - 40 - 90) / 6);
  var stats = [
    { icon: 'PEND', val: '12', label: 'Pending',    color: C.warning,   bg: C.warningL },
    { icon: 'ACCP', val: '8',  label: 'Accepted',   color: C.info,      bg: C.infoL   },
    { icon: 'PREP', val: '5',  label: 'Preparing',  color: C.purple,    bg: C.purpleL },
    { icon: 'DISP', val: '7',  label: 'Dispatched', color: C.secondary, bg: C.tealL   },
    { icon: 'COMP', val: '143',label: 'Completed',  color: C.success,   bg: C.successL},
    { icon: 'RJCT', val: '3',  label: 'Rejected',   color: C.danger,    bg: C.dangerL },
  ];
  stats.forEach(function(s, i) {
    statCard(f, cx + i * (cardW + 14), cy + 36, cardW, s.icon, s.val, s.label, s.color, s.bg);
  });
  var chartY = cy + 152, chartW = CW - 40 - 240;
  card(f, cx, chartY, chartW, 240, 'Orders Overview (This Week)');
  var bars = [18, 24, 15, 31, 28, 22, 12];
  var days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  var bw2 = 32, bx0 = cx + 20, by0 = chartY + 44 + 160, sc = 4;
  bars.forEach(function(v, i) {
    var bh = v * sc;
    R(f, bx0 + i * (bw2 + 18), by0 - bh, bw2, bh, i === 3 ? C.secondary : C.primary, 3);
    T(f, bx0 + i * (bw2 + 18) + 4, by0 - bh - 16, String(v), 9, 'Regular', C.textMid);
    T(f, bx0 + i * (bw2 + 18) + 4, by0 + 6, days[i], 9, 'Regular', C.textMid);
  });
  var dox = cx + chartW + 16;
  card(f, dox, chartY, 218, 240, 'Order Status');
  E(f, dox + 54, chartY + 64, 110, 110, C.border);
  E(f, dox + 76, chartY + 86, 66, 66, C.surface);
  T(f, dox + 86, chartY + 104, '178', 16, 'Bold', C.text);
  T(f, dox + 86, chartY + 124, 'Total', 9, 'Regular', C.textMid);
  var legends = [['Pending', C.warning], ['Accepted', C.primary], ['Completed', C.success], ['Rejected', C.danger]];
  legends.forEach(function(l, i) {
    R(f, dox + 16, chartY + 184 + i * 14, 10, 10, l[1], 2);
    T(f, dox + 30, chartY + 182 + i * 14, l[0], 10, 'Regular', C.textMid);
  });
  var tableY = chartY + 256;
  card(f, cx, tableY, chartW, 300, 'Recent Orders');
  btn(f, cx + chartW - 100, tableY + 10, 90, 'View All', 'outline');
  tbl(f, cx, tableY + 44, chartW,
    ['Order ID', 'Customer', 'Type', 'Amount', 'Status', 'Action'],
    [['#ORD-1024', 'Rahul Sharma',  'Regular', 'Rs 1,440', 'Pending',    'View'],
     ['#ORD-1023', 'Priya Kumar',   'Rx',      'Rs 2,880', 'Accepted',   'View'],
     ['#ORD-1022', 'Anjali Mehta',  'Regular', 'Rs 960',   'Preparing',  'View'],
     ['#ORD-1021', 'Suresh Kumar',  'Regular', 'Rs 3,120', 'Dispatched', 'View'],
     ['#ORD-1020', 'Neha Patel',    'Rx',      'Rs 1,680', 'Completed',  'View']]
  );
  card(f, dox, tableY, 218, 300, 'Quick Actions');
  ['Add Product', 'View Orders', 'Prescriptions', 'Reports'].forEach(function(b, i) {
    btn(f, dox + 12, tableY + 56 + i * 52, 194, b, 'outline');
  });
  return f;
}

function buildProducts(W) {
  var H = 900; var f = F('04_Products_List', W, H, C.bg);
  sidebar(f, H, 'products');
  topnav(f, W, 'Products', 'Medicine & Product Master');
  var cx = SW + 20, cy = NH + 20, CW = W - SW;
  T(f, cx, cy, 'Medicine & Product Master', 20, 'Bold', C.text);
  btn(f, W - 210, cy, 190, '+ Add New Product', 'primary');
  card(f, cx, cy + 44, CW - 40, 760);
  inp(f, cx + 10, cy + 56, 220, null, 'Search by name or SKU...');
  inp(f, cx + 240, cy + 56, 160, null, 'All Categories');
  tbl(f, cx, cy + 106, CW - 40,
    ['#', 'Product', 'Category', 'Unit', 'MRP (Rs)', 'Disc', 'Rx', 'Status', 'Actions'],
    [['1', 'Amoxicillin 500mg',  'Antibiotics',   'Strip/10',  'Rs 85',  '20%', 'Yes', 'Active', 'Edit Del'],
     ['2', 'Paracetamol 650mg',  'Analgesics',    'Strip/15',  'Rs 33',  '20%', 'No',  'Active', 'Edit Del'],
     ['3', 'Vitamin D3 1000IU',  'Vitamins',      'Bottle/60', 'Rs 280', '20%', 'No',  'Active', 'Edit Del'],
     ['4', 'Metformin 500mg',    'Diabetic Care', 'Strip/10',  'Rs 45',  '20%', 'Yes', 'Active', 'Edit Del'],
     ['5', 'Omeprazole 20mg',    'Antacids',      'Strip/14',  'Rs 68',  '20%', 'No',  'Inactive','Edit Del'],
     ['6', 'Atorvastatin 10mg',  'Cardio',        'Strip/10',  'Rs 95',  '20%', 'Yes', 'Active', 'Edit Del'],
     ['7', 'Cetirizine 10mg',    'Antihistamine', 'Strip/10',  'Rs 28',  '20%', 'No',  'Active', 'Edit Del'],
     ['8', 'Pantoprazole 40mg',  'Antacids',      'Strip/14',  'Rs 55',  '20%', 'Yes', 'Active', 'Edit Del']]
  );
  return f;
}

function buildAddProduct(W) {
  var H = 1020; var f = F('05_Add_Product', W, H, C.bg);
  sidebar(f, H, 'products');
  topnav(f, W, 'Products > Add New Product', '');
  var cx = SW + 20, cy = NH + 20, CW = W - SW;
  var fw = Math.min(880, CW - 40), hw = Math.floor((fw - 32) / 2), tw = Math.floor((fw - 48) / 3);
  T(f, cx, cy, 'Add New Product', 20, 'Bold', C.text);
  btn(f, cx + fw - 130, cy, 120, 'Back', 'secondary');
  card(f, cx, cy + 50, fw, 290, 'Basic Information');
  inp(f, cx + 14, cy + 106, hw, 'Product / Medicine Name *', 'e.g., Amoxicillin 500mg');
  inp(f, cx + 14 + hw + 16, cy + 106, hw, 'Generic Name', 'e.g., Amoxicillin');
  inp(f, cx + 14, cy + 176, hw, 'SKU / Product Code', 'Auto-generate');
  inp(f, cx + 14 + hw + 16, cy + 176, hw, 'Manufacturer / Brand', 'e.g., Sun Pharma');
  inp(f, cx + 14, cy + 246, hw, 'Category *', '-- Select Category --');
  inp(f, cx + 14 + hw + 16, cy + 246, hw, 'Sub-Category', '-- Select Sub-Category --');
  card(f, cx, cy + 356, fw, 130, 'Pricing');
  inp(f, cx + 14, cy + 412, tw, 'MRP (Rs) *', '0.00');
  inp(f, cx + 14 + tw + 16, cy + 412, tw, 'Discount %', '20');
  inp(f, cx + 14 + (tw + 16) * 2, cy + 412, tw, 'Selling Price (auto)', '');
  card(f, cx, cy + 504, fw, 170, 'Product Details');
  inp(f, cx + 14, cy + 560, hw, 'Unit of Measure *', 'Strip / Bottle / Piece');
  inp(f, cx + 14 + hw + 16, cy + 560, hw, 'Pack Size', 'e.g., 10 Tablets per Strip');
  inp(f, cx + 14, cy + 630, fw, 'Storage Instructions', 'e.g., Store below 25 deg C');
  btn(f, cx + fw - 360, H - 50, 110, 'Cancel', 'secondary');
  btn(f, cx + fw - 240, H - 50, 110, 'Save Draft', 'outline');
  btn(f, cx + fw - 120, H - 50, 110, 'Add Product', 'primary');
  return f;
}

function buildOrders(W) {
  var H = 920; var f = F('08_Orders_List', W, H, C.bg);
  var CW = W - SW;
  sidebar(f, H, 'orders');
  topnav(f, W, 'Orders', 'Order Management');
  var cx = SW + 20, cy = NH + 20;
  T(f, cx, cy, 'Order Management', 20, 'Bold', C.text);
  R(f, cx, cy + 44, CW - 40, 46, C.surface, 0, C.border);
  var tabs = ['All (35)', 'Pending (12)', 'Accepted (8)', 'Preparing (5)', 'Dispatched (7)', 'Completed (143)', 'Rejected (3)'];
  var tx = cx + 8;
  tabs.forEach(function(tab, i) {
    var isA = i === 0, tw2 = tab.length * 7 + 20;
    if (isA) R(f, tx, cy + 78, tw2, 2, C.primary);
    T(f, tx + 8, cy + 57, tab, 12, isA ? 'Semi Bold' : 'Regular', isA ? C.primary : C.textMid);
    tx += tw2 + 8;
  });
  card(f, cx, cy + 90, CW - 40, 740);
  inp(f, cx + 10, cy + 102, 220, null, 'Search order ID or customer...');
  inp(f, cx + 240, cy + 102, 140, null, 'Date');
  inp(f, cx + 390, cy + 102, 130, null, 'All Types');
  tbl(f, cx, cy + 150, CW - 40,
    ['Order ID', 'Customer', 'Type', 'Items', 'Total', 'Date', 'Status', 'Actions'],
    [['#ORD-1024', 'Rahul Sharma',  'Regular', '3 items', 'Rs 1,440', '12 Aug 10:32', 'Pending',    'View Acc Rej'],
     ['#ORD-1023', 'Priya Kumar',   'Rx',      '5 items', 'Rs 2,880', '12 Aug 09:18', 'Accepted',   'View'],
     ['#ORD-1022', 'Anjali Mehta',  'Regular', '2 items', 'Rs 960',   '12 Aug 08:55', 'Preparing',  'View'],
     ['#ORD-1021', 'Suresh Kumar',  'Regular', '6 items', 'Rs 3,120', '11 Aug 04:10', 'Dispatched', 'View'],
     ['#ORD-1020', 'Neha Patel',    'Rx',      '4 items', 'Rs 1,680', '11 Aug 02:45', 'Completed',  'View'],
     ['#ORD-1019', 'Vijay Raj',     'Regular', '1 item',  'Rs 240',   '11 Aug 11:20', 'Rejected',   'View']]
  );
  return f;
}

function buildOrderDetail(W) {
  var H = 1020; var f = F('09_Order_Detail', W, H, C.bg);
  var CW = W - SW;
  sidebar(f, H, 'orders');
  topnav(f, W, 'Orders > #ORD-1024', '');
  var cx = SW + 20, cy = NH + 20;
  btn(f, cx, cy, 130, 'Back to Orders', 'secondary');
  R(f, cx, cy + 42, CW - 40, 76, C.primary, 10);
  T(f, cx + 18, cy + 52, '#ORD-1024', 22, 'Bold', C.white);
  T(f, cx + 18, cy + 82, '12 Aug 2026  10:32 AM  |  Regular Order  |  COD', 11, 'Regular', { r:0.9, g:0.9, b:0.95 }, CW - 200);
  btn(f, CW - 90, cy + 54, 80, 'Accept', 'success');
  btn(f, CW - 180, cy + 54, 80, 'Reject', 'danger');
  var lw = Math.floor((CW - 40) * 0.63), rw = CW - 40 - lw - 16, detY = cy + 134;
  card(f, cx, detY, lw, 116, 'Customer Information');
  E(f, cx + 14, detY + 56, 44, 44, C.primary);
  T(f, cx + 22, detY + 68, 'RS', 13, 'Bold', C.white);
  T(f, cx + 68, detY + 54, 'Rahul Sharma', 14, 'Bold', C.text);
  T(f, cx + 68, detY + 74, '+91-9876543210  |  rahul@email.com', 11, 'Regular', C.textMid, lw - 82);
  card(f, cx, detY + 130, lw, 310, 'Order Items');
  tbl(f, cx, detY + 174, lw,
    ['Product', 'Qty', 'MRP', 'Disc', 'Amount'],
    [['Amoxicillin 500mg', '2', 'Rs 85.00', '20%', 'Rs 136.00'],
     ['Vitamin D3 1000IU', '1', 'Rs 280.00','20%', 'Rs 224.00'],
     ['Paracetamol 650mg', '5', 'Rs 32.50', '20%', 'Rs 130.00']]
  );
  T(f, cx + lw - 140, detY + 420, 'Total Payable:', 13, 'Bold', C.text);
  T(f, cx + lw - 20, detY + 420, 'Rs 478', 13, 'Bold', C.primary);
  var rx = cx + lw + 16;
  card(f, rx, detY, rw, 148, 'Update Status');
  inp(f, rx + 12, detY + 56, rw - 24, null, 'Pending');
  btn(f, rx + 12, detY + 100, rw - 24, 'Update Status', 'primary');
  card(f, rx, detY + 162, rw, 200, 'Order Timeline');
  ['Order Placed', 'Awaiting Acceptance', 'Accepted', 'Preparing', 'Dispatched'].forEach(function(tl, i) {
    R(f, rx + 18, detY + 210 + i * 36 + 3, 10, 10, i === 0 ? C.success : i === 1 ? C.primary : C.border, 5);
    T(f, rx + 36, detY + 210 + i * 36, tl, 12, i < 2 ? 'Semi Bold' : 'Regular', i < 2 ? C.text : C.textMid, rw - 50);
  });
  return f;
}

function buildBill(W) {
  var H = 900; var f = F('10_Generate_Bill', W, H, C.bg);
  var CW = W - SW;
  sidebar(f, H, 'orders');
  topnav(f, W, 'Orders > #ORD-1024 > Generate Bill', '');
  var cx = SW + 20, cy = NH + 20;
  T(f, cx, cy, 'Generate Order Bill', 20, 'Bold', C.text);
  btn(f, W - 220, cy, 90, 'Print', 'outline');
  btn(f, W - 120, cy, 110, 'Download PDF', 'outline');
  var bw = 660, bx = cx + Math.floor((CW - 40 - bw) / 2);
  R(f, bx, cy + 50, bw, 700, C.surface, 10, C.border);
  R(f, bx, cy + 50, bw, 6, C.primary);
  T(f, bx + 220, cy + 72, 'Shridhar Warehouse', 18, 'Bold', C.primary);
  T(f, bx + 180, cy + 98, 'Jamshedpur, Jharkhand  |  +91-7004310455', 11, 'Regular', C.textMid);
  LN(f, bx + 20, cy + 118, bw - 40);
  T(f, bx + 270, cy + 128, 'TAX INVOICE', 15, 'Bold', C.text);
  LN(f, bx + 20, cy + 150, bw - 40);
  T(f, bx + 20, cy + 162, 'Bill No.: BILL-2026-0892', 12, 'Semi Bold', C.primary);
  T(f, bx + 300, cy + 162, 'Date: 12 Aug 2026  |  Order: #ORD-1024', 12, 'Regular', C.text);
  T(f, bx + 20, cy + 190, 'Customer: Rahul Sharma  |  +91-9876543210  |  12 MG Road, Jamshedpur', 12, 'Regular', C.text, bw - 40);
  LN(f, bx + 20, cy + 214, bw - 40);
  tbl(f, bx + 20, cy + 220, bw - 40,
    ['#', 'Product', 'Qty', 'MRP (Rs)', 'Disc', 'Amount (Rs)'],
    [['1', 'Amoxicillin 500mg (Strip/10)',  '2', '85.00', '20%', '136.00'],
     ['2', 'Vitamin D3 1000IU (Bottle/60)', '1', '280.00','20%', '224.00'],
     ['3', 'Paracetamol 650mg (Strip/15)',  '5', '32.50', '20%', '130.00']]
  );
  var ty = cy + 450;
  T(f, bx + bw - 220, ty, 'Sub Total:', 12, 'Regular', C.textMid); T(f, bx + bw - 60, ty, 'Rs 597.50', 12, 'Regular', C.text);
  T(f, bx + bw - 220, ty + 20, 'Discount (20%):', 12, 'Regular', C.textMid); T(f, bx + bw - 80, ty + 20, '- Rs 119.50', 12, 'Semi Bold', C.success);
  LN(f, bx + bw - 230, ty + 44, 210);
  T(f, bx + bw - 220, ty + 52, 'Total Payable:', 14, 'Bold', C.text); T(f, bx + bw - 80, ty + 52, 'Rs 478.00', 14, 'Bold', C.primary);
  LN(f, bx + 20, ty + 76, bw - 40);
  T(f, bx + 160, ty + 88, 'Thank you!  Powered by SG Softech', 10, 'Regular', C.textMid);
  return f;
}

function buildPrescriptions(W) {
  var H = 900; var f = F('11_Prescriptions', W, H, C.bg);
  var CW = W - SW;
  sidebar(f, H, 'prescriptions');
  topnav(f, W, 'Prescriptions', 'Prescription Management');
  var cx = SW + 20, cy = NH + 20;
  T(f, cx, cy, 'Prescription Management', 20, 'Bold', C.text);
  var tabs2 = ['All (18)', 'Pending (4)', 'Approved (6)', 'Rejected (2)'];
  R(f, cx, cy + 44, CW - 40, 46, C.surface, 0, C.border);
  tabs2.forEach(function(tab, i) {
    var isA = i === 0, tx2 = cx + 8 + i * 140;
    if (isA) R(f, tx2, cy + 78, 80, 2, C.primary);
    T(f, tx2 + 8, cy + 57, tab, 12, isA ? 'Semi Bold' : 'Regular', isA ? C.primary : C.textMid);
  });
  card(f, cx, cy + 90, CW - 40, 740);
  tbl(f, cx, cy + 90, CW - 40,
    ['Rx ID', 'Customer', 'Uploaded', 'Linked Order', 'Images', 'Status', 'Actions'],
    [['#RX-0048', 'Priya Kumar  +91-8765432109',   '12 Aug 10 mins', '#ORD-1023', '2 images', 'Pending',  'View Review'],
     ['#RX-0047', 'Amit Singh  +91-7654321098',    '12 Aug 35 mins', '#ORD-1022', '1 image',  'Pending',  'View Review'],
     ['#RX-0046', 'Neha Patel  +91-5432109876',    '11 Aug 02:30 PM','#ORD-1020', '1 image',  'Approved', 'View'],
     ['#RX-0045', 'Vijay Raj  +91-4321098765',     '11 Aug 11:10 AM','#ORD-1019', '1 image',  'Rejected', 'View']]
  );
  return f;
}

function buildUsers(W) {
  var H = 840; var f = F('14_User_Management', W, H, C.bg);
  var CW = W - SW;
  sidebar(f, H, 'users');
  topnav(f, W, 'Users', 'User Management');
  var cx = SW + 20, cy = NH + 20;
  T(f, cx, cy, 'User Management', 20, 'Bold', C.text);
  btn(f, W - 210, cy, 190, '+ Add New User', 'primary');
  R(f, cx, cy + 44, CW - 40, 40, C.infoL, 6);
  R(f, cx, cy + 44, 4, 40, C.info);
  T(f, cx + 16, cy + 54, 'Phase 1 includes 3 user licenses. Currently using 2 of 3.', 11, 'Regular', C.info, CW - 60);
  card(f, cx, cy + 98, CW - 40, 280);
  tbl(f, cx, cy + 98, CW - 40,
    ['#', 'User', 'Role', 'Last Login', 'Status', 'Actions'],
    [['1', 'Admin User  |  admin@warehouse.com',     'Administrator',       '12 Aug 10:30 AM', 'Active', 'Edit'],
     ['2', 'Operator  |  operator@warehouse.com',    'Warehouse Operator',  '12 Aug 09:15 AM', 'Active', 'Edit Del'],
     ['3', '-- License Slot Available --',           '--',                  '--',              '--',     '+ Add']]
  );
  var mx = cx + 100, my = cy + 400, mhw = 196;
  R(f, SW, 0, CW, H, C.black).opacity = 0.4;
  R(f, mx, my, 460, 340, C.surface, 12, C.border);
  R(f, mx, my, 460, 52, C.gray1);
  LN(f, mx, my + 52, 460);
  T(f, mx + 18, my + 16, 'Add New User', 16, 'Bold', C.text);
  inp(f, mx + 18, my + 64, mhw, 'Full Name *', 'Enter full name');
  inp(f, mx + 18 + mhw + 10, my + 64, mhw, 'Email *', 'user@warehouse.com');
  inp(f, mx + 18, my + 134, mhw, 'Phone', '+91-XXXXXXXXXX');
  inp(f, mx + 18 + mhw + 10, my + 134, mhw, 'Role *', '-- Select Role --');
  inp(f, mx + 18, my + 204, 424, 'Password *', 'Set initial password');
  btn(f, mx + 270, my + 278, 90, 'Cancel', 'secondary');
  btn(f, mx + 368, my + 278, 76, 'Add User', 'primary');
  return f;
}

function buildSettings(W) {
  var H = 880; var f = F('15_System_Settings', W, H, C.bg);
  var CW = W - SW;
  sidebar(f, H, 'settings');
  topnav(f, W, 'Settings', 'System Settings');
  var cx = SW + 20, cy = NH + 20;
  T(f, cx, cy, 'System Settings', 20, 'Bold', C.text);
  var snw = 200, mx2 = cx + snw + 16, mw = CW - 40 - snw - 16;
  card(f, cx, cy + 44, snw, 400);
  var sItems = ['Business Config', 'Warehouse Config', 'Product Config', 'Discount Settings', 'Order Settings', 'Notifications', 'System Status'];
  sItems.forEach(function(item, i) {
    var isA = i === 0, iy = cy + 44 + i * 52;
    if (isA) { R(f, cx, iy, 4, 52, C.primary); R(f, cx, iy, snw, 52, C.blueL); }
    T(f, cx + 16, iy + 18, item, 12, isA ? 'Semi Bold' : 'Regular', isA ? C.primary : C.textMid, snw - 32);
    if (i < sItems.length - 1) LN(f, cx, iy + 52, snw);
  });
  card(f, mx2, cy + 44, mw, 680, 'Business Configuration');
  btn(f, mx2 + mw - 130, cy + 56, 120, 'Save Changes', 'primary');
  var hw2 = Math.floor((mw - 48) / 2);
  inp(f, mx2 + 16, cy + 104, hw2, 'Business / Warehouse Name *', 'Shridhar Warehouse');
  inp(f, mx2 + 16 + hw2 + 16, cy + 104, hw2, 'Owner Name', 'Mr. Shridhar');
  inp(f, mx2 + 16, cy + 176, hw2, 'Email', 'shridhar@warehouse.com');
  inp(f, mx2 + 16 + hw2 + 16, cy + 176, hw2, 'Phone', '+91-7004310455');
  inp(f, mx2 + 16, cy + 248, mw - 32, 'Address', 'Jamshedpur, Jharkhand 831001');
  inp(f, mx2 + 16, cy + 320, hw2, 'GST Number', 'Enter GSTIN');
  inp(f, mx2 + 16 + hw2 + 16, cy + 320, hw2, 'Drug License No.', 'Enter License No.');
  LN(f, mx2 + 16, cy + 398, mw - 32);
  T(f, mx2 + 16, cy + 410, 'DISCOUNT CONFIGURATION', 9, 'Bold', C.textMid, mw - 32);
  inp(f, mx2 + 16, cy + 430, hw2, 'Global Discount %', '20');
  T(f, mx2 + 16, cy + 498, 'Applied automatically to all customer cart totals', 11, 'Regular', C.textMid, mw - 32);
  return f;
}

function buildReports(W) {
  var H = 820; var f = F('16_Reports', W, H, C.bg);
  var CW = W - SW;
  sidebar(f, H, 'reports');
  topnav(f, W, 'Reports', 'View and export operational reports');
  var cx = SW + 20, cy = NH + 20;
  T(f, cx, cy, 'Reports', 20, 'Bold', C.text);
  var rcs = [
    { title: 'Order Summary',     desc: 'Total orders, status, revenue',   p: 1 },
    { title: 'Customer History',  desc: 'All orders per customer',          p: 1 },
    { title: 'Product Sales',     desc: 'Top products, qty, revenue',       p: 1 },
    { title: 'Daily Summary',     desc: 'Orders & revenue by day',          p: 1 },
    { title: 'Prescription Report',desc: 'Rx orders, approval rates',       p: 1 },
    { title: 'Rejected Orders',   desc: 'Rejected orders + reasons',        p: 1 },
    { title: 'Stock Movement',    desc: 'Inventory in/out tracking',        p: 2 },
    { title: 'P&L Report',        desc: 'Financial profit/loss statement',  p: 2 },
    { title: 'Delivery Report',   desc: 'Delivery performance stats',       p: 2 },
  ];
  var rcw = Math.floor((CW - 40 - 32) / 3);
  rcs.forEach(function(rc, i) {
    var col = i % 3, row = Math.floor(i / 3);
    var rx2 = cx + col * (rcw + 16), ry2 = cy + 50 + row * 136;
    R(f, rx2, ry2, rcw, 120, rc.p === 2 ? C.gray1 : C.surface, 8, C.border);
    T(f, rx2 + 12, ry2 + 12, rc.title, 14, 'Semi Bold', C.text, rcw - 24);
    T(f, rx2 + 12, ry2 + 36, rc.desc, 11, 'Regular', C.textMid, rcw - 24);
    badge(f, rx2 + 12, ry2 + 90, rc.p === 1 ? 'Phase 1' : 'Phase 2', rc.p === 1 ? C.successL : C.gray1, rc.p === 1 ? C.success : C.textMid, 56);
    if (rc.p === 1) btn(f, rx2 + rcw - 96, ry2 + 80, 84, 'Download', 'outline');
    else T(f, rx2 + 12, ry2 + 56, 'Available in Phase 2', 10, 'Regular', C.textMid, rcw - 24);
  });
  return f;
}

function buildGeneric(name, activeKey, W) {
  var H = 860; var f = F(name, W, H, C.bg);
  var CW = W - SW;
  sidebar(f, H, activeKey);
  topnav(f, W, name.replace(/_/g, ' '), '');
  var cx = SW + 20, cy = NH + 20, fw = CW - 40, hw = Math.floor((fw - 32) / 2);
  T(f, cx, cy, name.replace(/_/g, ' '), 20, 'Bold', C.text);
  card(f, cx, cy + 44, fw, 440, name.replace(/_/g, ' '));
  inp(f, cx + 16, cy + 104, hw, 'Field 1 *', 'Enter value');
  inp(f, cx + 16 + hw + 16, cy + 104, hw, 'Field 2', 'Enter value');
  inp(f, cx + 16, cy + 176, hw, 'Field 3', 'Enter value');
  inp(f, cx + 16 + hw + 16, cy + 176, hw, 'Field 4', 'Enter value');
  btn(f, cx + fw - 240, cy + 420, 110, 'Cancel', 'secondary');
  btn(f, cx + fw - 120, cy + 420, 110, 'Save', 'primary');
  return f;
}

function arrangeExisting(opts) {
  var frames = figma.currentPage.children
    .filter(function(n) { return n.type === 'FRAME'; })
    .sort(function(a, b) { return a.name.localeCompare(b.name); });
  var x = 100;
  frames.forEach(function(fr) {
    fr.x = x; fr.y = 100;
    x += opts.frameWidth + opts.frameGap;
  });
  if (opts.addPrototype) {
    for (var i = 0; i < frames.length - 1; i++) {
      try {
        frames[i].reactions = [{ action: { type: 'NODE', destinationId: frames[i + 1].id, navigation: 'NAVIGATE', transition: { type: 'SMART_ANIMATE', easing: { type: 'EASE_OUT' }, duration: 0.3 }, preserveScrollPosition: false }, trigger: { type: 'ON_CLICK' } }];
      } catch(e) {}
    }
  }
  figma.viewport.scrollAndZoomIntoView(frames);
}

async function generateScreens(opts) {
  var W = opts.frameWidth, GAP = opts.frameGap;
  var page = figma.currentPage;
  var frames = [], x = 100;
  var total = opts.screens.length;
  for (var i = 0; i < total; i++) {
    var s = opts.screens[i];
    figma.ui.postMessage({ type: 'PROGRESS', pct: Math.round(((i + 0.5) / total) * 90), text: 'Building ' + s.name + '...' });
    var fr = null;
    try {
      if      (s.id === 'login')       fr = buildLogin(W);
      else if (s.id === 'forgot')      fr = buildGeneric('02_Forgot_Password', 'login', W);
      else if (s.id === 'dashboard')   fr = buildDashboard(W);
      else if (s.id === 'products')    fr = buildProducts(W);
      else if (s.id === 'addproduct')  fr = buildAddProduct(W);
      else if (s.id === 'editproduct') fr = buildGeneric('06_Edit_Product', 'products', W);
      else if (s.id === 'categories')  fr = buildGeneric('07_Categories', 'categories', W);
      else if (s.id === 'orders')      fr = buildOrders(W);
      else if (s.id === 'orderdetail') fr = buildOrderDetail(W);
      else if (s.id === 'bill')        fr = buildBill(W);
      else if (s.id === 'presclist')   fr = buildPrescriptions(W);
      else if (s.id === 'prescreview') fr = buildGeneric('12_Prescription_Review', 'prescriptions', W);
      else if (s.id === 'profile')     fr = buildGeneric('13_Warehouse_Profile', 'settings', W);
      else if (s.id === 'users')       fr = buildUsers(W);
      else if (s.id === 'settings')    fr = buildSettings(W);
      else if (s.id === 'reports')     fr = buildReports(W);
      else                             fr = buildGeneric(s.num + '_' + s.name.replace(/ /g, '_'), s.id, W);
      if (fr) {
        fr.x = x; fr.y = 100;
        page.appendChild(fr);
        frames.push(fr);
        if (opts.addLabels) {
          var lbl = figma.createText();
          lbl.fontName = { family: 'Inter', style: 'Bold' };
          lbl.fontSize = 20;
          lbl.fills = [{ type: 'SOLID', color: C.textMid }];
          lbl.characters = s.num + '. ' + s.name;
          lbl.x = x; lbl.y = 100 + fr.height + 20;
          page.appendChild(lbl);
        }
        x += W + GAP;
      }
    } catch(err) { console.error('Error on ' + s.id + ': ' + err.message); }
  }
  if (opts.addPrototype && frames.length > 1) {
    for (var j = 0; j < frames.length - 1; j++) {
      try {
        frames[j].reactions = [{ action: { type: 'NODE', destinationId: frames[j + 1].id, navigation: 'NAVIGATE', transition: { type: 'SMART_ANIMATE', easing: { type: 'EASE_OUT' }, duration: 0.3 }, preserveScrollPosition: false }, trigger: { type: 'ON_CLICK' } }];
      } catch(e) {}
    }
  }
  figma.viewport.scrollAndZoomIntoView(frames);
  figma.ui.postMessage({ type: 'PROGRESS', pct: 100, text: 'Done!' });
}