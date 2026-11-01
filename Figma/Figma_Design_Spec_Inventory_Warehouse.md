# 🎨 Figma Design Specification
## Inventory & Warehouse Management Web Application
**Client:** Mr. Shridhar, Jamshedpur, Jharkhand
**Project By:** SG Softech
**Date:** 05 Aug 2026

---

## 📐 Design System & Foundations

### Color Palette
| Token | Color | Hex |
|-------|-------|-----|
| Primary | Deep Blue | `#1A3C6E` |
| Secondary | Teal | `#0F9B8E` |
| Accent | Orange | `#F57C00` |
| Success | Green | `#2E7D32` |
| Warning | Amber | `#F9A825` |
| Danger | Red | `#C62828` |
| Info | Light Blue | `#0277BD` |
| Background | Light Gray | `#F5F7FA` |
| Surface | White | `#FFFFFF` |
| Text Primary | Dark | `#1C1C1E` |
| Text Secondary | Gray | `#6B7280` |
| Border | Light | `#E5E7EB` |
| Sidebar BG | Dark Blue | `#0F2744` |
| Sidebar Text | White | `#FFFFFF` |

### Typography
| Style | Font | Size | Weight |
|-------|------|------|--------|
| H1 Page Title | Inter | 28px | 700 |
| H2 Section Title | Inter | 22px | 600 |
| H3 Card Title | Inter | 18px | 600 |
| Body Regular | Inter | 14px | 400 |
| Body Small | Inter | 12px | 400 |
| Label | Inter | 13px | 500 |
| Button Text | Inter | 14px | 600 |
| Badge/Tag | Inter | 11px | 500 |

### Spacing Scale
`4px · 8px · 12px · 16px · 24px · 32px · 48px · 64px`

### Border Radius
`4px (inputs) · 8px (cards) · 12px (modals) · 50px (pills/badges)`

### Breakpoints
| Name | Width |
|------|-------|
| Desktop HD | 1440px |
| Desktop | 1280px |
| Tablet | 768px |

---

## 🧩 Reusable Components Library

### 1. Navigation Sidebar
```
Width: 260px (expanded) / 64px (collapsed)
BG: #0F2744
Items: Icon + Label
Active state: Left border accent (#F57C00) + bg highlight
Hover: bg rgba(255,255,255,0.08)
```
**Sidebar Menu Items:**
- 🏠 Dashboard
- 📦 Products / Medicine Master
- 🗂️ Product Categories
- 🛒 Orders
- 📋 Prescriptions
- 🏭 Inventory (Phase 2)
- 🚚 Delivery (Phase 2)
- 💰 Accounting (Phase 2)
- 📊 Reports
- ⚙️ Settings / Admin
- 👥 User Management
- 🔔 Notifications

### 2. Top Navigation Bar
```
Height: 64px
BG: #FFFFFF
Shadow: 0 2px 8px rgba(0,0,0,0.08)
Contains:
  - Left: Hamburger menu (collapse sidebar) + Page breadcrumb
  - Right: Search bar + Notification bell (badge) + User avatar + Dropdown
```

### 3. Stat Cards (Dashboard)
```
Width: ~280px (4 per row on 1280px)
Height: 110px
BG: White
Border-radius: 8px
Shadow: 0 2px 12px rgba(0,0,0,0.06)
Contains:
  - Icon (colored bg circle, 44px)
  - Metric number (H2 bold)
  - Label (body small, secondary text)
  - Trend indicator (↑↓ arrow + % change)
```

### 4. Data Table
```
Header: bg #F9FAFB, font-weight 600, text #374151
Row height: 52px
Alternating rows: white / #FAFAFA
Action column: Edit (blue) | View (gray) | Delete (red) icons
Pagination: Previous / Page numbers / Next
Per page selector: 10 / 25 / 50
```

### 5. Status Badges / Pills
| Status | BG | Text |
|--------|----|------|
| Pending | `#FFF3CD` | `#856404` |
| Accepted | `#D1ECF1` | `#0C5460` |
| Under Preparation | `#CCE5FF` | `#004085` |
| Dispatched | `#D4EDDA` | `#155724` |
| Completed | `#D4EDDA` | `#155724` |
| Rejected | `#F8D7DA` | `#721C24` |
| Active | `#D1FAE5` | `#065F46` |
| Inactive | `#F3F4F6` | `#6B7280` |

### 6. Buttons
| Type | BG | Text | Use |
|------|----|------|-----|
| Primary | `#1A3C6E` | White | Main actions |
| Secondary | `#E5E7EB` | `#374151` | Cancel/Back |
| Success | `#2E7D32` | White | Accept/Confirm |
| Danger | `#C62828` | White | Reject/Delete |
| Outline | Transparent | `#1A3C6E` | Secondary actions |
| Icon Button | Transparent | Icon only | Table actions |

### 7. Form Elements
```
Input height: 40px
Border: 1px solid #D1D5DB
Focus border: 2px solid #1A3C6E
Border-radius: 6px
Label: 13px, weight 500, color #374151
Helper text: 12px, color #6B7280
Error text: 12px, color #C62828
```

### 8. Modal / Dialog
```
Overlay: rgba(0,0,0,0.5)
Modal width: 480px / 640px / 800px
Header: Title + X close button
Footer: Cancel + Confirm buttons (right aligned)
Border-radius: 12px
```

### 9. Toast Notifications
```
Position: Top-right
Width: 320px
Types: Success (green) | Error (red) | Warning (amber) | Info (blue)
Duration: 3-5 seconds auto dismiss
```

---

## 📄 Screen Inventory (All Pages)

---

## SCREEN 1 — Login Page

**Route:** `/login`
**Layout:** Split screen (50/50)

### Left Panel
- Background: Gradient `#1A3C6E → #0F9B8E`
- Company Logo (centered, white)
- Tagline: *"Simplifying Warehouse Operations"*
- Illustration: Warehouse/inventory SVG graphic
- Feature bullets (3 items with icons)

### Right Panel
- White background
- "Welcome Back" heading
- Sub-text: *"Login to Inventory & Warehouse Management"*
- **Form Fields:**
  - Email / Username (input)
  - Password (input with show/hide toggle)
  - Remember Me (checkbox)
  - Forgot Password? (link, right aligned)
- **Login Button** (full-width, primary)
- Footer: SG Softech branding + version

### States
- Default | Loading (spinner in button) | Error (red border + message) | Success

---

## SCREEN 2 — Forgot Password

**Route:** `/forgot-password`
**Layout:** Centered card (480px wide)

- Back to Login link
- Email input
- Send Reset Link button
- Confirmation state (email sent message with illustration)

---

## SCREEN 3 — Dashboard (Home)

**Route:** `/dashboard`
**Layout:** Sidebar + Top Nav + Main Content

### Stat Cards Row 1 (Order Summary)
| Card | Icon | Color |
|------|------|-------|
| Pending Orders | 🕐 Clock | Amber |
| Accepted Orders | ✅ Check | Blue |
| Under Preparation | 🔄 Process | Purple |
| Dispatched Orders | 🚚 Truck | Teal |
| Completed Orders | 📦 Box | Green |
| Rejected Orders | ❌ X | Red |

### Charts Section
- **Left (60%):** Bar Chart — Orders by Day/Week/Month (filter toggle)
- **Right (40%):** Donut Chart — Order Status Distribution

### Recent Orders Table
- Columns: Order ID | Customer | Products | Amount | Status | Date | Actions
- Show 10 rows with View button
- "View All Orders" link

### Quick Actions Panel
- + Add New Product
- + Receive New Order
- 📋 View Pending Prescriptions
- 📊 Generate Report

### Low Stock Alert Widget (Phase 2 — placeholder)
- List of 5 items with stock count < threshold

---

## SCREEN 4 — Product / Medicine Master List

**Route:** `/products`
**Layout:** Sidebar + Top Nav + Full Page Table

### Page Header
- Title: "Medicine & Product Master"
- Breadcrumb: Dashboard > Products
- Right: `+ Add New Product` button

### Filter Bar
- Search input (by name, SKU, category)
- Category dropdown filter
- Availability filter (All / Available / Unavailable)
- Export button (CSV/Excel)

### Products Table
| Column | Details |
|--------|---------|
| # | Row number |
| Product Image | Thumbnail (40x40px) |
| Product Name | Bold, clickable |
| Category | Badge |
| MRP (₹) | Right aligned |
| Availability | Toggle switch (Active/Inactive) |
| Stock | Quantity (Phase 2) |
| Actions | Edit ✏️ \| View 👁️ \| Delete 🗑️ |

### Pagination
- Bottom: showing X–Y of Z results

---

## SCREEN 5 — Add New Product

**Route:** `/products/add`
**Layout:** Sidebar + Top Nav + Form Card

### Form Sections

**Section 1: Basic Information**
- Product Name* (text input)
- Generic Name (text input)
- SKU / Product Code (text input, auto-generate option)
- Category* (dropdown — from Category Master)
- Sub-Category (dropdown, conditional)
- Manufacturer / Brand (text input)
- Description (textarea, 3 rows)

**Section 2: Pricing**
- MRP (₹)* (number input)
- Selling Price (₹) (number input)
- Discount % (auto-calculated or manual)
- GST % (dropdown: 0%, 5%, 12%, 18%) — Phase 2

**Section 3: Product Details**
- Unit of Measure (dropdown: Strip, Bottle, Tablet, Piece, Box, Pack)
- Pack Size (e.g., "10 Tablets per Strip")
- Prescription Required (Yes/No toggle)
- Storage Instructions (text)

**Section 4: Product Image**
- Drag & Drop image upload area
- Supported: JPG, PNG, max 2MB
- Preview thumbnail

**Section 5: Availability**
- Product Status (Active / Inactive toggle)

### Footer Buttons
- Cancel (secondary) | Save as Draft | Add Product (primary)

---

## SCREEN 6 — Edit Product

**Route:** `/products/edit/:id`
- Same layout as Add Product, fields pre-filled
- Additional: "Last Updated" info at top

---

## SCREEN 7 — Product Categories

**Route:** `/categories`
**Layout:** Sidebar + Top Nav + Split View

### Left: Category Tree / List
- List of main categories with expand arrow
- Sub-categories nested below
- Add Category button
- Search categories

### Right: Category Detail / Form
- Category Name*
- Parent Category (dropdown — for sub-category)
- Description
- Icon/Image upload
- Status (Active/Inactive)
- Save button

### Category Table View (alternate)
| Column |
|--------|
| Category Name |
| Parent Category |
| Products Count |
| Status |
| Actions (Edit / Delete) |

---

## SCREEN 8 — Orders List

**Route:** `/orders`
**Layout:** Sidebar + Top Nav + Full Page

### Tab Navigation
```
[ All Orders ] [ Pending ] [ Accepted ] [ Under Preparation ] [ Dispatched ] [ Completed ] [ Rejected ]
```
Each tab shows count badge.

### Filter Bar
- Date range picker
- Search by Order ID / Customer name
- Sort by: Date | Amount | Status

### Orders Table
| Column | Details |
|--------|---------|
| Order ID | #ORD-XXXX (clickable) |
| Customer Name | Name + phone |
| Order Type | Regular / Prescription badge |
| Items | Count of products |
| Total Amount | ₹ amount |
| Order Date & Time | DD MMM YYYY, HH:MM |
| Status | Colored badge |
| Actions | View 👁️ \| Accept ✅ \| Reject ❌ |

---

## SCREEN 9 — Order Detail View

**Route:** `/orders/:id`
**Layout:** Sidebar + Top Nav + Detail Page

### Order Header Card
- Order ID (large, bold) + Status badge
- Order Date | Order Type (Regular/Prescription)
- Accept Order / Reject Order buttons (if Pending)

### Two-Column Layout

**Left Column (65%)**

**Customer Information Card**
- Name, Phone, Address
- Customer History link

**Order Items Card**
| Product | Qty | MRP | Discount | Amount |
|---------|-----|-----|----------|--------|
| Med name | 2 | ₹120 | 20% | ₹192 |

**Order Summary**
- Sub Total
- Discount (20%)
- **Total Payable**
- Payment Mode: COD

**Prescription Card** (if prescription order)
- Uploaded prescription image with zoom
- Doctor name (if available)
- Review notes textarea
- Approve / Request Clarification buttons

**Right Column (35%)**

**Order Timeline Card**
```
🔵 Order Placed — 10:30 AM
🔵 Order Accepted — 10:45 AM
🟡 Under Preparation — 11:00 AM
⚪ Dispatched
⚪ Delivered
```

**Action Panel Card**
- Update Status dropdown
- Assign Delivery (Phase 2)
- Add Notes (textarea)
- Generate Bill button

**Bill Preview Card** (after bill generated)
- Bill No., Date
- Item list, Total
- Print / Download PDF buttons

---

## SCREEN 10 — Generate Order Bill

**Route:** `/orders/:id/bill`
**Layout:** Modal (800px) or Full page

### Bill Form
- Bill Number (auto-generated)
- Bill Date (date picker)
- Customer Details (auto-filled)
- Items Table (editable qty, price)
- Discount line
- GST (Phase 2)
- Total Amount
- Payment Mode: COD

### Actions
- Preview | Print | Save & Generate | Download PDF

---

## SCREEN 11 — Prescriptions

**Route:** `/prescriptions`
**Layout:** Sidebar + Top Nav + Card Grid or Table

### Tab Navigation
```
[ All ] [ Pending Review ] [ Reviewed ] [ Approved ] [ Rejected ]
```

### Prescription Cards / Table
| Field |
|-------|
| Prescription ID |
| Customer Name + Phone |
| Upload Date |
| Linked Order ID |
| Status Badge |
| Actions: View | Review | Approve | Reject |

---

## SCREEN 12 — Prescription Detail / Review

**Route:** `/prescriptions/:id`
**Layout:** Split View

**Left: Image Viewer**
- Prescription image (zoomable, rotatable)
- Navigation for multiple images
- Download button

**Right: Review Form**
- Customer info
- Notes / observations textarea
- Medicines extracted (manual entry table):
  - Medicine Name | Qty | Dosage | Duration
- Add to Order button
- Approve / Reject buttons with reason

---

## SCREEN 13 — Profile / Warehouse Settings

**Route:** `/profile`
**Layout:** Sidebar + Top Nav + Settings Layout

### Tabs
- **Business Profile** | **Account Settings** | **Change Password**

**Business Profile Form**
- Warehouse/Business Name*
- Owner Name*
- Email*
- Phone*
- Address (Street, City, State, PIN)
- GST Number
- License Number
- Business Logo (upload)
- Operating Hours

**Account Settings**
- Username
- Email (verified badge)
- Two-Factor Auth toggle (Phase 2)

**Change Password**
- Current Password
- New Password
- Confirm New Password
- Strength indicator

---

## SCREEN 14 — User Management

**Route:** `/settings/users`
**Layout:** Sidebar + Top Nav + Table

### User Table
| Column |
|--------|
| Name |
| Email |
| Role (Admin / Operator / Billing Executive) |
| Last Login |
| Status (Active/Inactive toggle) |
| Actions: Edit | Delete |

### Add / Edit User Modal
- Full Name*
- Email*
- Phone
- Role* (dropdown)
- Password (for new user)
- Status toggle

> ⚠️ **Note:** Phase 1 includes 3 user licenses. Additional users: ₹10,000/user.

---

## SCREEN 15 — Admin: Core Settings

**Route:** `/settings/system`
**Layout:** Sidebar + Top Nav + Settings Panel with sub-nav

### Sub-Navigation (Left side list)
- General / Business Configuration
- Inventory/Warehouse Configuration
- Product Configuration
- Discount Configuration
- MRP Management
- Product Availability Management
- Order Management Settings
- Notification Settings
- System Status

### General Settings Form
- Business Name
- Default Currency
- Time Zone
- Date Format
- Application Language

### Discount Configuration
- Global Discount % (e.g., 20%)
- Enable/Disable discount toggle
- Discount applies to: All Products / Specific Categories

### Order Management Settings
- Auto-accept orders toggle
- Order notification (Email/In-App)
- Order ID prefix format (e.g., ORD-)

---

## SCREEN 16 — Reports

**Route:** `/reports`
**Layout:** Sidebar + Top Nav + Reports Hub

### Report Cards Grid
| Report | Icon |
|--------|------|
| Order Summary Report | 📋 |
| Customer Order History | 👤 |
| Product Sales Report | 📦 |
| Daily / Weekly / Monthly Summary | 📅 |
| Prescription Orders Report | 💊 |
| Rejected Orders Report | ❌ |

### Report Detail Page
- Date range filter
- Additional filters (category, product, customer)
- Summary stats at top
- Data table
- Export: CSV / PDF / Print

---

## SCREEN 17 — Notifications

**Route:** `/notifications`
**Layout:** Sidebar + Top Nav + Notification List

### Notification Items
- Icon (color coded by type)
- Title + Description
- Time ago
- Unread indicator (blue dot)
- Mark as read / Delete

### Notification Types
- 🛒 New Order Received
- 💊 New Prescription Upload
- ⚠️ Low Stock Alert (Phase 2)
- ✅ Order Completed
- ❌ Order Rejected

---

## PHASE 2 SCREENS (Design Placeholders)

---

## SCREEN 18 — Purchase Management (Phase 2)

**Route:** `/purchase`
**Sub-pages:**
- Purchase Orders List + Add PO form
- Supplier Quotations
- Goods Receipt Note (GRN)
- Purchase Invoice
- Supplier Returns

---

## SCREEN 19 — Inventory Management (Phase 2)

**Route:** `/inventory`
**Sub-pages:**
- Warehouse Master
- Stock Entry form
- Stock Adjustment
- Batch & Expiry Management
- Stock Availability view
- Stock Movement log

---

## SCREEN 20 — Delivery Management (Phase 2)

**Route:** `/delivery`
**Sub-pages:**
- Delivery Boy list + Add form
- Delivery Assignment
- Route Planning (map view)
- Delivery Tracking
- OTP Delivery confirmation

---

## SCREEN 21 — Accounting (Phase 2)

**Route:** `/accounting`
**Sub-pages:**
- Ledger
- Cash Book / Bank Book
- Journal / Payment / Receipt / Contra Vouchers
- GST Reports
- P&L / Balance Sheet / Trial Balance

---

## SCREEN 22 — CRM (Phase 2)

**Route:** `/crm`
**Sub-pages:**
- Customer Follow-up
- Loyalty Program
- Customer Wallet

---

## SCREEN 23 — Analytics Dashboard (Phase 2)

**Route:** `/analytics`
- Business Dashboard (KPI overview)
- Sales Analytics (charts, trends)
- Inventory Analytics
- Purchase Analytics

---

## 🗂️ Figma File Structure

```
📁 Inventory & Warehouse Management — Figma
│
├── 📄 Cover Page
├── 📄 Design System
│   ├── 🎨 Colors
│   ├── 📝 Typography
│   ├── 📏 Spacing & Grid
│   └── 🧩 Components Library
│       ├── Buttons
│       ├── Inputs & Forms
│       ├── Cards
│       ├── Tables
│       ├── Badges & Pills
│       ├── Sidebar & Navbar
│       ├── Modals
│       └── Toast / Alerts
│
├── 📄 Authentication
│   ├── Login
│   └── Forgot Password
│
├── 📄 Dashboard
│   └── Main Dashboard
│
├── 📄 Product Management
│   ├── Product List
│   ├── Add Product
│   ├── Edit Product
│   └── Product Categories
│
├── 📄 Order Management
│   ├── Orders List (All Tabs)
│   ├── Order Detail
│   └── Generate Bill
│
├── 📄 Prescription Management
│   ├── Prescription List
│   └── Prescription Review
│
├── 📄 Settings & Admin
│   ├── Profile / Warehouse Settings
│   ├── User Management
│   └── Core System Settings
│
├── 📄 Reports
│   └── Reports Hub + Detail
│
├── 📄 Notifications
│
└── 📄 Phase 2 Wireframes (Low Fidelity)
    ├── Purchase Management
    ├── Inventory Management
    ├── Delivery Management
    ├── Accounting
    ├── CRM
    └── Analytics
```

---

## 📱 Responsive Considerations

### Desktop (1280px — Primary)
- Sidebar: 260px fixed left
- Content: remaining width
- Grid: 12 column

### Desktop Compact (1024px)
- Sidebar: Collapsible to 64px
- Cards: 3 per row instead of 4

### Tablet (768px)
- Sidebar: Hidden, accessible via hamburger
- Cards: 2 per row
- Tables: Horizontal scroll

---

## 🔄 Key User Flows for Prototyping

### Flow 1: Login → Dashboard
`Login Page → Dashboard`

### Flow 2: Receive & Process Order
`Dashboard → Orders (Pending tab) → Order Detail → Accept Order → Under Preparation → Generate Bill → Dispatch`

### Flow 3: Add New Product
`Products List → Add Product Form → Save → Product List (updated)`

### Flow 4: Prescription Order Flow
`Prescriptions → Prescription Detail → Review → Approve/Reject → Link to Order`

### Flow 5: Add User
`Settings → User Management → Add User Modal → Save → User List`

---

## 📋 Figma Design Checklist

### Setup
- [ ] Create Figma project: *"IWM — Inventory & Warehouse Management"*
- [ ] Setup color styles from Design System
- [ ] Setup text styles (H1–Body)
- [ ] Create component variants for buttons, inputs, badges
- [ ] Build sidebar and top nav as master components

### Phase 1 Screens
- [ ] Login page
- [ ] Forgot Password
- [ ] Dashboard
- [ ] Product List
- [ ] Add/Edit Product
- [ ] Product Categories
- [ ] Orders List (all tabs)
- [ ] Order Detail
- [ ] Generate Bill
- [ ] Prescription List
- [ ] Prescription Review
- [ ] Profile Settings
- [ ] User Management
- [ ] System Settings
- [ ] Reports

### Phase 2 Screens (Wireframes)
- [ ] Purchase Management
- [ ] Inventory Management
- [ ] Delivery Management
- [ ] Accounting
- [ ] CRM
- [ ] Analytics

### Prototype
- [ ] Login → Dashboard flow
- [ ] Order processing flow
- [ ] Add product flow
- [ ] Prescription review flow

---

*Prepared for: Mr. Shridhar, Jamshedpur | By: SG Softech | support@sgsoftech.in*
