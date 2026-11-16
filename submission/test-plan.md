# Approved test plan

Source of truth: `runs/run-20261116-093132/test_cases.json` (approved by `bansa` at 2026-11-16T10:32:49, sha256 `dd4799d157a1...`).

**48 cases**: 31 API, 17 UI. TC-010 was removed during review (redundant with TC-048). IDs are kept stable, so the numbering has a gap.

## API cases

| ID | Title | Type | Priority | Module covered | Test file |
|---|---|---|---|---|---|
| TC-001 | Sign-up with valid data creates user | positive | P1 | `backend/app/api/routes/users.py` | `generated/api/test_users.py` |
| TC-002 | Sign-up with duplicate email rejected | negative | P1 | `backend/app/api/routes/users.py` | `generated/api/test_users.py` |
| TC-003 | Sign-up with invalid email format | negative | P2 | `backend/app/api/routes/users.py` | `generated/api/test_users.py` |
| TC-004 | Sign-up password below minimum length (7 chars) | boundary | P2 | `backend/app/api/routes/users.py` | `generated/api/test_users.py` |
| TC-005 | Sign-up password at boundary lengths (8 and 128 chars) accepted, 129 rejected | boundary | P2 | `backend/app/api/routes/users.py` | `generated/api/test_users.py` |
| TC-006 | Login with valid credentials returns token | positive | P1 | `backend/app/api/routes/login.py` | `generated/api/test_login.py` |
| TC-007 | Login with wrong password | negative | P1 | `backend/app/api/routes/login.py` | `generated/api/test_login.py` |
| TC-008 | Login with non-existent user | negative | P2 | `backend/app/api/routes/login.py` | `generated/api/test_login.py` |
| TC-009 | Login with missing form fields | negative | P3 | `backend/app/api/routes/login.py` | `generated/api/test_login.py` |
| TC-011 | Tampered or invalid JWT rejected | negative | P1 | `backend/app/api/deps.py` | `generated/api/test_login.py` |
| TC-012 | Create item with valid payload | positive | P1 | `backend/app/api/routes/items.py` | `generated/api/test_items.py` |
| TC-013 | Create item without title | negative | P2 | `backend/app/api/routes/items.py` | `generated/api/test_items.py` |
| TC-014 | Item title boundary: empty, 1, 255, 256 chars | boundary | P2 | `backend/app/api/routes/items.py` | `generated/api/test_items.py` |
| TC-015 | Item description boundary 255 / 256 chars | boundary | P3 | `backend/app/api/routes/items.py` | `generated/api/test_items.py` |
| TC-016 | Items endpoints require authentication | negative | P1 | `backend/app/api/routes/items.py` | `generated/api/test_items.py` |
| TC-017 | List items returns only own items | positive | P1 | `backend/app/api/routes/items.py` | `generated/api/test_items.py` |
| TC-018 | Get item owned by another user | negative | P1 | `backend/app/api/routes/items.py` | `generated/api/test_items.py` |
| TC-019 | Update another user's item is blocked | negative | P1 | `backend/app/api/routes/items.py` | `generated/api/test_items.py` |
| TC-020 | Delete another user's item is blocked | negative | P1 | `backend/app/api/routes/items.py` | `generated/api/test_items.py` |
| TC-021 | Owner updates and deletes own item | positive | P1 | `backend/app/api/routes/items.py` | `generated/api/test_items.py` |
| TC-022 | Get item with non-existent or malformed id | negative | P2 | `backend/app/api/routes/items.py` | `generated/api/test_items.py` |
| TC-023 | Get own profile | positive | P1 | `backend/app/api/routes/users.py` | `generated/api/test_users.py` |
| TC-024 | Update own profile (full_name, email) | positive | P2 | `backend/app/api/routes/users.py` | `generated/api/test_users.py` |
| TC-025 | Update own email to an existing user's email | negative | P2 | `backend/app/api/routes/users.py` | `generated/api/test_users.py` |
| TC-026 | Change password with correct current password | positive | P1 | `backend/app/api/routes/users.py` | `generated/api/test_users.py` |
| TC-027 | Change password with wrong current password or same password | negative | P2 | `backend/app/api/routes/users.py` | `generated/api/test_users.py` |
| TC-028 | Normal user cannot access admin user endpoints | negative | P1 | `backend/app/api/routes/users.py` | `generated/api/test_users.py` |
| TC-029 | Delete own account removes user | positive | P2 | `backend/app/api/routes/users.py` | `generated/api/test_users.py` |
| TC-030 | Superuser cannot delete own account | negative | P2 | `backend/app/api/routes/users.py` | `generated/api/test_users.py` |
| TC-048 | Users endpoints reject requests with no token | negative | P1 | `backend/app/api/routes/users.py` | `generated/api/test_users.py` |
| TC-049 | Item write operations reject requests with no token | negative | P1 | `backend/app/api/routes/items.py` | `generated/api/test_items.py` |

## UI cases

| ID | Title | Type | Priority | Module covered | Test file |
|---|---|---|---|---|---|
| TC-031 | Sign up via UI form | positive | P1 | `frontend/src/routes/signup.tsx` | `generated/ui/auth.spec.ts` |
| TC-032 | Sign-up validation: mismatched passwords | negative | P2 | `frontend/src/routes/signup.tsx` | `generated/ui/auth.spec.ts` |
| TC-033 | Sign-up validation: short password and invalid email | boundary | P2 | `frontend/src/routes/signup.tsx` | `generated/ui/auth.spec.ts` |
| TC-034 | Sign-up with an already registered email | negative | P2 | `frontend/src/routes/signup.tsx` | `generated/ui/auth.spec.ts` |
| TC-035 | Login via UI with valid credentials | positive | P1 | `frontend/src/routes/login.tsx` | `generated/ui/auth.spec.ts` |
| TC-036 | Login via UI with wrong password | negative | P1 | `frontend/src/routes/login.tsx` | `generated/ui/auth.spec.ts` |
| TC-037 | Login form empty and invalid email validation | negative | P3 | `frontend/src/routes/login.tsx` | `generated/ui/auth.spec.ts` |
| TC-038 | Unauthenticated access to protected route redirects to login | negative | P1 | `frontend/src/routes/_layout.tsx` | `generated/ui/auth.spec.ts` |
| TC-039 | Create item through the UI | positive | P1 | `frontend/src/routes/_layout/items.tsx` | `generated/ui/items.spec.ts` |
| TC-040 | Item form requires title and enforces max length | boundary | P2 | `frontend/src/routes/_layout/items.tsx` | `generated/ui/items.spec.ts` |
| TC-041 | Edit item through the UI | positive | P2 | `frontend/src/routes/_layout/items.tsx` | `generated/ui/items.spec.ts` |
| TC-042 | Delete item through the UI with confirmation | positive | P2 | `frontend/src/routes/_layout/items.tsx` | `generated/ui/items.spec.ts` |
| TC-043 | Items list shows only the logged-in user's items | positive | P1 | `frontend/src/routes/_layout/items.tsx` | `generated/ui/items.spec.ts` |
| TC-044 | Update profile in settings | positive | P2 | `frontend/src/routes/_layout/settings.tsx` | `generated/ui/settings.spec.ts` |
| TC-045 | Change password in settings | positive | P1 | `frontend/src/routes/_layout/settings.tsx` | `generated/ui/settings.spec.ts` |
| TC-046 | Change password validation: mismatch and wrong current | negative | P2 | `frontend/src/routes/_layout/settings.tsx` | `generated/ui/settings.spec.ts` |
| TC-047 | Non-superuser cannot access admin page | negative | P2 | `frontend/src/routes/_layout/admin.tsx` | `generated/ui/admin.spec.ts` |

## Steps and expected results

**TC-001 Sign-up with valid data creates user** (API, positive, P1)
1. POST /api/v1/users/signup with unique email, password of 8+ chars, full_name
- Expected: 200 with user public data (id, email, is_active=true, is_superuser=false); the response has no password or hashed_password.

**TC-002 Sign-up with duplicate email rejected** (API, negative, P1)
1. Sign up user A
2. POST /api/v1/users/signup again with the same email
- Expected: 400 with a detail saying the user already exists; no second record is created.

**TC-003 Sign-up with invalid email format** (API, negative, P2)
1. POST /api/v1/users/signup with email 'not-an-email'
- Expected: 422 validation error pointing at the email field.

**TC-004 Sign-up password below minimum length (7 chars)** (API, boundary, P2)
1. POST /api/v1/users/signup with a 7-character password
- Expected: 422 (password min_length 8 violated); no user is created.

**TC-005 Sign-up password at boundary lengths (8 and 128 chars) accepted, 129 rejected** (API, boundary, P2)
1. Sign up with an 8-char password
2. Sign up with a 128-char password
3. Sign up with a 129-char password
- Expected: The first two return 200; the third returns 422.

**TC-006 Login with valid credentials returns token** (API, positive, P1)
1. POST /api/v1/login/access-token as form data (username=email, password)
- Expected: 200 with access_token and token_type='bearer'.

**TC-007 Login with wrong password** (API, negative, P1)
1. POST /api/v1/login/access-token with a valid email and a wrong password
- Expected: 400 'Incorrect email or password'; no token is issued.

**TC-008 Login with non-existent user** (API, negative, P2)
1. POST /api/v1/login/access-token with an unregistered email
- Expected: 400 with the same generic message as a wrong password, so there is no user enumeration.

**TC-009 Login with missing form fields** (API, negative, P3)
1. POST /api/v1/login/access-token with an empty body
- Expected: 422 listing the missing username and password.

**TC-011 Tampered or invalid JWT rejected** (API, negative, P1)
1. GET /api/v1/users/me with Authorization: Bearer <token with altered signature>
- Expected: 403 'Could not validate credentials'.

**TC-012 Create item with valid payload** (API, positive, P1)
1. Log in as user A
2. POST /api/v1/items/ with title and description
- Expected: 200 with item id, matching title and description, and owner_id equal to user A's id.

**TC-013 Create item without title** (API, negative, P2)
1. POST /api/v1/items/ with body {"description":"x"}
- Expected: 422 with a missing title error.

**TC-014 Item title boundary: empty, 1, 255, 256 chars** (API, boundary, P2)
1. POST /api/v1/items/ with title lengths 0, 1, 255 and 256
- Expected: Lengths 1 and 255 return 200; lengths 0 and 256 return 422.

**TC-015 Item description boundary 255 / 256 chars** (API, boundary, P3)
1. POST /api/v1/items/ with a 255-char description
2. POST /api/v1/items/ with a 256-char description
- Expected: 255 returns 200; 256 returns 422.

**TC-016 Items endpoints require authentication** (API, negative, P1)
1. Call GET, POST, PUT and DELETE on /api/v1/items/ and /api/v1/items/{id} without a token
- Expected: Every call returns 401 status (message text not asserted).

**TC-017 List items returns only own items** (API, positive, P1)
1. User A creates 2 items and user B creates 1
2. GET /api/v1/items/ as A
- Expected: 200 with data containing only A's 2 items and count=2.

**TC-018 Get item owned by another user** (API, negative, P1)
1. User B creates an item
2. GET /api/v1/items/{id} with A's token
- Expected: 403 'Not enough permissions' and no item data in the body.

**TC-019 Update another user's item is blocked** (API, negative, P1)
1. PUT /api/v1/items/{B's item id} with A's token and a new title
2. GET the item as B
- Expected: PUT returns 403; the item is unchanged.

**TC-020 Delete another user's item is blocked** (API, negative, P1)
1. DELETE /api/v1/items/{B's item id} with A's token
2. GET the item as B
- Expected: DELETE returns 403; the item still exists.

**TC-021 Owner updates and deletes own item** (API, positive, P1)
1. PUT /api/v1/items/{id} with a new title
2. DELETE /api/v1/items/{id}
3. GET /api/v1/items/{id}
- Expected: PUT returns 200 with the updated title; DELETE returns 200 with a success message; the final GET returns 404.

**TC-022 Get item with non-existent or malformed id** (API, negative, P2)
1. GET /api/v1/items/{random valid UUID}
2. GET /api/v1/items/abc
- Expected: The UUID request returns 404 'Item not found'; the malformed id returns 422.

**TC-023 Get own profile** (API, positive, P1)
1. GET /api/v1/users/me with a valid token
- Expected: 200 with the current user's email and full_name.

**TC-024 Update own profile (full_name, email)** (API, positive, P2)
1. PATCH /api/v1/users/me with a new full_name and email
- Expected: 200 with the updated values, which GET /users/me confirms.

**TC-025 Update own email to an existing user's email** (API, negative, P2)
1. As user A, PATCH /api/v1/users/me with user B's email
- Expected: 409 'User with this email already exists'; A's email is unchanged.

**TC-026 Change password with correct current password** (API, positive, P1)
1. PATCH /api/v1/users/me/password with current_password and a valid new_password
2. Log in with the new password
3. Log in with the old password
- Expected: PATCH returns 200; the new password logs in; the old password returns 400.

**TC-027 Change password with wrong current password or same password** (API, negative, P2)
1. PATCH /api/v1/users/me/password with a wrong current_password
2. PATCH with new_password equal to current_password
- Expected: Both return 400 and the password is unchanged.

**TC-028 Normal user cannot access admin user endpoints** (API, negative, P1)
1. With a non-superuser token, GET /api/v1/users/
2. GET /api/v1/users/{other user id}
3. PATCH and DELETE /api/v1/users/{other user id}
- Expected: Each call returns 403 'The user doesn't have enough privileges'.

**TC-029 Delete own account removes user** (API, positive, P2)
1. DELETE /api/v1/users/me as a normal user
2. Log in again with the same credentials
- Expected: DELETE returns 200; the later login fails with 400.

**TC-030 Superuser cannot delete own account** (API, negative, P2)
1. DELETE /api/v1/users/me with a superuser token
- Expected: 403 'Super users are not allowed to delete themselves'.

**TC-031 Sign up via UI form** (UI, positive, P1)
1. Open /signup
2. Enter full name, a unique email, a password, and the matching confirm password
3. Click Sign Up
- Expected: The account is created and the user is redirected to /login, with a success toast if one is shown.

**TC-032 Sign-up validation: mismatched passwords** (UI, negative, P2)
1. Open /signup
2. Enter different values in Password and Confirm Password
3. Submit
- Expected: An inline error says the passwords don't match; no API call is made.

**TC-033 Sign-up validation: short password and invalid email** (UI, boundary, P2)
1. Enter an invalid email
2. Enter a 7-character password
3. Submit
- Expected: Inline errors appear for the email and for the minimum password length of 8; the form is not submitted.

**TC-034 Sign-up with an already registered email** (UI, negative, P2)
1. Submit the sign-up form with an existing email
- Expected: An error toast or message says the user already exists, and the user stays on /signup.

**TC-035 Login via UI with valid credentials** (UI, positive, P1)
1. Open /login
2. Enter valid email and password
3. Click Log In
- Expected: The user is redirected to the dashboard, a token is stored, and the user's name or email shows in the layout.

**TC-036 Login via UI with wrong password** (UI, negative, P1)
1. Enter a valid email and a wrong password
2. Submit
- Expected: An error message such as 'Incorrect email or password' appears and the user stays on /login.

**TC-037 Login form empty and invalid email validation** (UI, negative, P3)
1. Submit with empty fields
2. Submit with an invalid email format
- Expected: Inline validation errors appear and no request is sent.

**TC-038 Unauthenticated access to protected route redirects to login** (UI, negative, P1)
1. Clear local storage
2. Navigate directly to /items and /settings
- Expected: Both redirect to /login.

**TC-039 Create item through the UI** (UI, positive, P1)
1. Log in
2. Open /items
3. Click Add Item
4. Enter title and description
5. Save
- Expected: The dialog closes and the new item appears in the table.

**TC-040 Item form requires title and enforces max length** (UI, boundary, P2)
1. Open Add Item
2. Submit with an empty title
3. Enter a 256-char title and submit
- Expected: A required error shows for the empty title; a max-length error shows for 256 chars; no item is created.

**TC-041 Edit item through the UI** (UI, positive, P2)
1. On /items open the row actions menu
2. Click Edit Item
3. Change the title
4. Save
- Expected: The table row shows the updated title.

**TC-042 Delete item through the UI with confirmation** (UI, positive, P2)
1. Open row actions
2. Click Delete Item
3. Confirm in the dialog
- Expected: The item is removed from the list and a success toast appears. Cancelling the dialog keeps the item.

**TC-043 Items list shows only the logged-in user's items** (UI, positive, P1)
1. User A creates an item
2. Log out and log in as user B
3. Open /items
- Expected: B does not see A's items; an empty state shows if B has none.

**TC-044 Update profile in settings** (UI, positive, P2)
1. Open /settings, My profile tab
2. Edit full name
3. Save
- Expected: A success toast appears and the new name shows after reload.

**TC-045 Change password in settings** (UI, positive, P1)
1. Open the Password tab
2. Enter current password, new password and confirm
3. Save
4. Log out and log in with the new password
- Expected: A success toast appears and login works with the new password.

**TC-046 Change password validation: mismatch and wrong current** (UI, negative, P2)
1. Enter a mismatched confirm password and submit
2. Enter a wrong current password with matching new passwords and submit
- Expected: The mismatch is flagged inline with no request sent; the wrong current password shows an error toast from the API 400.

**TC-047 Non-superuser cannot access admin page** (UI, negative, P2)
1. Log in as a normal user
2. Check the sidebar for Admin
3. Navigate directly to /admin
- Expected: The Admin link is hidden and /admin shows no user management data (redirect or forbidden).

**TC-048 Users endpoints reject requests with no token** (API, negative, P1)
1. GET /api/v1/users/me with no Authorization header
2. PATCH /api/v1/users/me with no Authorization header
3. GET /api/v1/users/ with no Authorization header
- Expected: Each call returns 401 status; no user data returned.

**TC-049 Item write operations reject requests with no token** (API, negative, P1)
1. User A creates an item
2. POST /api/v1/items/ with no token
3. PUT /api/v1/items/{id} with no token
4. DELETE /api/v1/items/{id} with no token
- Expected: Each call returns 401 status; the item still exists unchanged for user A.
