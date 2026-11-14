# Campus Lost and Found

A modern, full-stack, enterprise-grade college web portal built with **Python 3.13**, **Django 5.2**, **MySQL 8.0**, and **Bootstrap 5**. The system enables students to report, search, and reclaim lost belongings across campus, while providing administrators with a robust governance suite for listing verification, confidential claim adjudication, concurrent approval locking, and physical item handover tracking.

---

## Table of Contents

- [Overview & Architecture](#overview--architecture)
- [Key Features](#key-features)
  - [Student Capabilities](#student-capabilities)
  - [Administrator Capabilities](#administrator-capabilities)
- [Technology Stack](#technology-stack)
- [Project Directory Structure](#project-directory-structure)
- [Installation & Local Setup](#installation--local-setup)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Clone Repository & Setup Virtual Environment](#2-clone-repository--setup-virtual-environment)
  - [3. Install Dependencies](#3-install-dependencies)
  - [4. MySQL Database Configuration](#4-mysql-database-configuration)
  - [5. Environment Variables Configuration](#5-environment-variables-configuration)
  - [6. Database Migrations](#6-database-migrations)
  - [7. Seed Initial Data & Create Admin](#7-seed-initial-data--create-admin)
  - [8. Run Development Server](#8-run-development-server)
- [Automated Testing Suite](#automated-testing-suite)
- [Security Specifications](#security-specifications)
- [DBMS Documentation & SQL Scripts](#dbms-documentation--sql-scripts)
- [License](#license)

---

## Overview & Architecture

Colleges and university campuses frequently experience misplaced belongings—such as student identity cards, laptops, calculators, laboratory manuals, keys, and wallets. Traditional notice boards and social media groups lack verification, confidentiality, structured search, and ownership proof.

**Campus Lost and Found** addresses this with a dual-role architecture:
- **Role-Based Access Control (RBAC):** Strict partition between `STUDENT` and `ADMIN` roles.
- **Verification Pipeline:** Newly submitted lost/found reports require administrative review before public display to prevent spam or inappropriate postings.
- **Confidential Claims System:** Claimants provide private ownership proof (e.g., serial numbers, unique scratches, internal contents) accessible only by administrators.
- **ACID-Compliant Concurrency Control:** Claim approvals use `transaction.atomic()` and row-level locks (`select_for_update()`) to prevent race conditions and conflicting approvals.
- **Handover Coordination:** Once a claim is approved, a secure internal messaging channel opens between the finder and verified claimant.

---

## Key Features

### Student Capabilities
- **Registration & Authentication:** Register with college credentials (Username, USN, College Email, Department, Semester, Phone). Secure password hashing and role enforcement.
- **Personal Dashboard:** Live metrics for total submissions, lost/found counts, active claims, unread notifications, and recent activity.
- **Item Reporting:**
  - Dedicated forms for **Lost Items** and **Found Items**.
  - Photo upload with client & server-side MIME type validation and 5 MB size limits.
  - Automatic `PENDING` verification status upon submission.
- **Listing & Search:**
  - Responsive card-based item browsing with badge indicators.
  - Multi-parameter search: keyword (name, description, location), category filter, date range, and sort order.
  - Server-side pagination using Django ORM.
- **Ownership Claims:**
  - Submit claim with detailed description and private proof of ownership.
  - Automated validation: Students cannot claim their own found items; duplicate pending claims for the same item are blocked at both model constraint and form levels.
- **Handover Coordination & Messaging:**
  - Secure conversation room for item handover once claim is approved.
  - Access restricted exclusively to verified claimant and finder.
- **Real-Time Notifications:**
  - Status updates on listing verification, claim approvals/rejections, and new messages.
  - AJAX unread count polling with badge counter in navigation bar.

### Administrator Capabilities
- **Admin Dashboard:**
  - Executive statistics: total students, total items, lost vs. found distribution, pending verifications, pending claims, and successfully returned counts.
  - Visual analytics: top reported categories and most active student reporters.
- **Student Account Management:**
  - Searchable student registry with department and status filters.
  - View comprehensive student activity history (all reports and claims).
  - One-click account activation and deactivation.
- **Item Listing Moderation:**
  - Review submitted lost and found reports.
  - Approve listings for public display or reject with administrative remarks.
  - Status history audit logging (`ItemStatusHistory`) for tracking state changes.
- **Claim Adjudication & Concurrency Protection:**
  - Review claimant information alongside confidential ownership proof.
  - Atomic approval: Approving a claim marks the item as `CLAIMED`, auto-rejects all competing pending claims, and notifies all affected students.
  - Official return marking: Transition item to `RETURNED` upon physical handover.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Backend Framework** | Python 3.13, Django 5.2 |
| **Database** | MySQL 8.0 (Production / Default), SQLite (Local Test Fallback) |
| **ORM & Architecture** | Django ORM, MVC/MVT, Atomic Transactions, Row-level Locking |
| **Frontend UI** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons |
| **Configuration** | `python-decouple`, `.env` |
| **Image Processing** | Pillow 13.0 |

---

## Project Directory Structure

```
campus-lost-and-found/
├── manage.py                          # Django CLI entrypoint
├── requirements.txt                   # Project Python dependencies
├── .env.example                       # Template for environment configuration
├── .env                               # Active environment configuration
├── .gitignore                         # Git exclusion rules
├── config/                            # Project core settings and routing
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py                    # Dual MySQL/SQLite DB config, auth, apps
│   ├── urls.py                        # Root URL dispatcher
│   └── wsgi.py
├── accounts/                          # User authentication & student profile app
│   ├── models.py                      # Custom User model (role, USN, dept)
│   ├── forms.py                       # Registration, Login, Profile forms
│   ├── views.py                       # Register, Login, Logout, Profile views
│   ├── urls.py
│   ├── admin.py                       # Django Admin user customization
│   └── tests.py                       # 10 automated authentication unit tests
├── lostfound/                         # Core domain logic, items, claims & messaging
│   ├── models.py                      # Category, Item, Claim, Message, Notification
│   ├── forms.py                       # ReportItemForm, ClaimForm, SearchForm
│   ├── views.py                       # Public, student, and admin moderation views
│   ├── services.py                    # Atomic business logic & concurrency handling
│   ├── urls.py
│   ├── admin.py
│   ├── tests.py                       # 23 comprehensive domain and RBAC tests
│   └── management/
│       └── commands/
│           └── seed_data.py           # Database seeder (admin, categories, demo items)
├── dashboard/                         # Analytical dashboards & student management
│   ├── views.py                       # Student & Admin dashboard controllers
│   ├── services.py                    # Database aggregation queries & metrics
│   └── urls.py
├── templates/                         # Modular HTML5 Django templates
│   ├── base.html                      # Global layout, sticky navbar, flash messages
│   ├── landing.html                   # Public portal landing page
│   ├── accounts/                      # login.html, register.html, profile.html
│   ├── components/                    # student_sidebar.html, admin_sidebar.html
│   ├── student/                       # dashboard, report_lost, report_found, etc.
│   └── admin_panel/                   # dashboard, items, claims, students, details
├── static/
│   ├── css/
│   │   └── style.css                  # Custom college theme (Navy, Teal, Slate)
│   └── js/
│       └── main.js                    # Dynamic alerts, previews, AJAX polling
├── sql/
│   └── demonstration_queries.sql      # Advanced SQL query demonstration file
├── DBMS_DOCUMENTATION.md              # Comprehensive DBMS design and ER documentation
└── README.md
```

---

## Installation & Local Setup

### 1. Prerequisites
- **Python 3.10+** (Python 3.13 recommended)
- **MySQL Server 8.0+**
- **Git**

### 2. Clone Repository & Setup Virtual Environment

```bash
git clone <repository-url>
cd campus-lost-and-found

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Windows (CMD):
.\venv\Scripts\activate.bat
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. MySQL Database Configuration

Log in to MySQL CLI or MySQL Workbench and create the application database:

```sql
CREATE DATABASE campus_lost_found_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Environment Variables Configuration

Copy `.env.example` to `.env`:

```bash
# On Windows:
copy .env.example .env
# On macOS/Linux:
cp .env.example .env
```

Open `.env` and fill in your MySQL credentials:

```ini
SECRET_KEY=your-secure-random-secret-key-here
DEBUG=True
DB_ENGINE=django.db.backends.mysql
DB_NAME=campus_lost_found_db
DB_USER=root
DB_PASSWORD=your-mysql-password
DB_HOST=127.0.0.1
DB_PORT=3306
```

*(Note: For local environments without a running MySQL server, setting `DB_ENGINE=django.db.backends.sqlite3` allows complete execution and testing using SQLite).*

### 6. Database Migrations

Apply the database schema:

```bash
python manage.py migrate
```

### 7. Seed Initial Data & Create Admin

Run the automated database seeder to populate campus categories, an admin user, sample students, and demo items:

```bash
python manage.py seed_data
```

**Default Seed Credentials:**
- **Administrator:** Username: `admin` | Password: `admin123`
- **Student 1:** Username: `student1` | Password: `student123`
- **Student 2:** Username: `student2` | Password: `student123`
- **Student 3:** Username: `student3` | Password: `student123`

You can also create a custom superuser manually:

```bash
python manage.py createsuperuser
```

### 8. Run Development Server

```bash
python manage.py runserver
```

Open your browser and navigate to:
- **Public Portal:** `http://127.0.0.1:8000/`
- **Login:** `http://127.0.0.1:8000/accounts/login/`
- **Django Admin:** `http://127.0.0.1:8000/django-admin/`

---

## Automated Testing Suite

The project includes 23 unit and integration tests verifying all core workflows, edge cases, authentication barriers, and database transactions:

```bash
# Run all tests
python manage.py test

# Run accounts tests
python manage.py test accounts

# Run lost and found domain tests
python manage.py test lostfound
```

### Test Coverage Highlights:
- **Authentication & Validation:** Registration with duplicate USN and email rejection, login authentication, deactivated account blocks, profile editing.
- **Reporting & Visibility:** Lost/found creation with `PENDING` verification, public listing filtration, 404 enforcement on unauthorized item views.
- **Claim Logic & Concurrency:** Own-item claim prevention, duplicate pending claim prevention, atomic approval, competing claim auto-rejection.
- **Authorization (RBAC):** Students blocked from admin routes, unauthenticated users redirected to login, private handover message privacy.

---

## Security Specifications

1. **Authentication & Password Security:** Utilizes Django's Argon2/PBKDF2 SHA-256 password hashing.
2. **Cross-Site Request Forgery (CSRF):** Protected via Django's `CsrfViewMiddleware` and `{% csrf_token %}` across all state-mutating forms.
3. **Role-Based Authorization:** Custom decorators `_admin_required` and `_student_required` protect all administrative endpoints.
4. **File Upload Hardening:** Validated against allowed image MIME types (`image/jpeg`, `image/png`, `image/gif`, `image/webp`) and strictly capped at 5 MB.
5. **Database Concurrency Protection:** Employs `@transaction.atomic` combined with `select_for_update()` to eliminate race conditions during claim approval.
6. **Confidentiality:** Claimant ownership evidence is hidden from public item detail pages and exposed only to verified administrators.

---

## DBMS Documentation & SQL Scripts

Comprehensive DBMS artifacts demonstrating Entity-Relationship modeling, 3NF normalization, relational schemas, data dictionary, and advanced SQL queries are provided:
- [DBMS_DOCUMENTATION.md](file:///c:/Users/CHANDRA/campus-lost-and-found/DBMS_DOCUMENTATION.md)
- [sql/demonstration_queries.sql](file:///c:/Users/CHANDRA/campus-lost-and-found/sql/demonstration_queries.sql)
