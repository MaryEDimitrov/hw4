# Homework 4 — Authentication harness notes

## Problem 4 — Authentication design

### What is stored for a user

New registrations write these fields to the `users` table:

- `id`: SQLite-generated user identifier.
- `name`: display name assembled from first and last name.
- `first_name` and `last_name`: separate profile fields for personalization.
- `email`: lowercased, unique login identifier.
- `password_hash`: salted password hash only; the raw password is never stored.
- `created_at`: SQLite-created account timestamp.

### How passwords are protected

The API uses Python's built-in `hashlib.scrypt` with a fresh random 16-byte salt for every new account. The stored value includes the algorithm parameters, salt, and derived key, but not the password. Login derives a new key using the submitted password and stored salt, then compares the values with `hmac.compare_digest`.

For compatibility with the supplied seed user, login also recognizes that database's legacy `pbkdf2_sha256` format (120,000 iterations). After a successful legacy login, the password is immediately re-hashed into the current salted scrypt format.

The frontend never receives a password hash. The login endpoint returns only a success flag and display name. Failed logins use one generic error for an unknown email or an incorrect password, reducing account-enumeration leakage. Passwords are also rejected unless they are at least 12 characters long.

### Verification results

- New-account registration and login were verified against a temporary copy of the database. The original seed database was not changed.
- The database contains exactly `test@campuscustoms.yale.edu`. Its legacy PBKDF2-SHA256 hash now validates the supplied password `password`, and a successful login migrates that record to scrypt. A brand-new account inserted into a temporary database copy also authenticated successfully. The seed database was not modified during testing.

## Problem 5 — Frontend, FastAPI, and agent flow

The React chat widget sends a JSON body containing the shopper's message and at most ten recent conversation turns to `POST /api/chat`. Vite proxies `/api` from the frontend on port 5173 to FastAPI on port 8000.

`backend/main.py` is the Uvicorn entry point. It validates the request, loads `PORTKEY_API_KEY` on the server, and calls `make_agent` from `backend/agent.py`. The agent loads `backend/prompts/prompt.md`, configures an OpenAI-compatible Portkey client, and uses `gpt-5.6-luna` by default. Its output is the typed `ChatResponse` from `backend/models.py`.

The agent can call the read-only SQLite tools in `backend/tools.py` to search products and retrieve descriptions, prices, colors, sizes, and stock. The browser receives only the structured reply; the API key, prompt, and tool internals stay server-side.

## Problem 6 — Database-backed product facts

The agent has three read-only database tools:

- `search_products` searches catalogue names, garment types, descriptions, colors, and tags.
- `get_product_details` retrieves the database description, price, colors, and every recorded size. Each size is labeled with its quantity or explicitly `out of stock` when quantity is zero.
- `check_stock` looks up exact inventory for all sizes or one requested size.

The system prompt requires a tool lookup before stating product facts. This prevents invented prices or quantities and makes zero-stock responses explicit.

### Tool return types and field choices

| Tool | Return type | Fields and why they matter |
|---|---|---|
| `search_products` | `list[ProductSearchHit]` | `product_id` identifies the catalogue record; `name` gives the shopper-facing label; `garment_type` supports category context; `price` enables price-oriented shortlisting. Search uses SQLite description, colors, and tags internally, but only concise result fields are returned to the agent. |
| `get_product_details` | `ProductDetails` | `product_id` connects the answer to the product card; `name` and `garment_type` identify the item; `description` supplies grounded product copy; `colors` answers color questions; `price` supplies the authoritative price; `sizes` includes every recorded size and labels zero quantity as out of stock. |
| `check_stock` | `StockLookupResult` | `product_id` identifies the inventory target; `requested_size` preserves whether the customer asked about one size; `stock` contains exact size-level quantities or an explicit out-of-stock/no-record message. |

The model fields are deliberately small and shopper-facing: they give the agent what it needs to answer accurately without exposing password data, database internals, or unrelated user records.

## Problem 7 — Structured chat search and page updates

`ChatResponse` is the API contract between the agent and the React widget. It contains the natural-language `reply`, `product_ids` for product linking, and `product_matches`, a list of `ProductSearchHit` objects. Each match contains `product_id`, `name`, `garment_type`, `price`, `description`, and `image_file_path` so the browser can render a complete product card without guessing or making a second search.

When a customer asks a category question such as “what hoodies do you have?”, the agent calls `search_products`, places the grounded matches in `product_matches`, and returns them from `POST /api/chat`. The widget immediately renders those matches inside the floating chat panel with the database image, name, price, and short description. The card remains clickable through the existing product-detail flow in the Products page.

Chat-card navigation is owned by the top-level React app: clicking a match passes its database `product_id` to the same Products-page selection state used by ordinary catalogue cards, switches to Products, and opens the existing large-image/full-information detail view. This keeps one detail-page behavior for both catalogue and chat results.

## Problem 8 — Customer memory

When a user logs in or creates an account, the API returns a minimal user context (`id`, `name`, and `email`) and the frontend keeps that context for the current browser session. The chat widget sends the user ID with each chat request. FastAPI looks up the authoritative name and email server-side, then creates `AgentDeps` with `user_name`, `user_email`, and `page_context`.

For logged-in users, each user and assistant turn is saved in `chat_messages`, including the assistant's product IDs in `products_json`. Opening the chat calls `GET /api/chat/history/{user_id}` and restores the prior conversation. Anonymous users can still chat, but their turns are not persisted.

When a shopper is viewing a product detail page, React passes a compact context object containing the product ID, name, description, colors, and price. The `/api/chat` prompt includes this as application context, so “do you have this in pink?” can be resolved by calling the database tools for that specific product rather than guessing.

### Memory contract

- Guests can use the chat widget normally. Their messages remain in the current browser session only and are not written to `chat_messages`.
- Logged-in users send their database `user_id` with each chat request. FastAPI resolves that ID to the authoritative `name` and `email` and saves both the user turn and assistant turn in `chat_messages`.
- Saved assistant rows include the response text and relevant product IDs in `products_json`; password hashes and raw passwords are never included.
- The agent receives only the customer fields needed for personalization—`user_name` and `user_email`—plus the current `page_context`. The page context is a compact JSON value containing the current product's `product_id`, name, description, colors, and price.
- On a later visit, the widget requests `/api/chat/history/{user_id}` and restores the saved role/content turns. Page context is freshly supplied from whichever product page the shopper is currently viewing.

Run the API from the backend folder:

```bash
cd "Homework/HW 4/backend"
uvicorn main:app --reload --port 8000
```

## Problem 10 — Storefront design system

The storefront combines a Yale-inspired blue/navy/cream foundation with Campus Customs’ pink gemstone accent color. `Playfair Display` provides the editorial serif voice for headlines and product names, while `DM Sans` keeps controls and long text clear.

Product cards use generous image space, clear garment labels, concise supporting copy, visible price hierarchy, hover lift, keyboard focus, and an Add to cart action. The home hero uses layered color, a custom Campus Customs shield mark, a campus badge, and restrained floating-card motion to create a memorable storefront entry point.

The chat panel uses a softer card treatment, a pink welcome accent, clear assistant/user message contrast, product-card results, and a gentle open animation so it feels like a concierge rather than a raw developer tool. Product, cart, and detail-page transitions use short motion cues, and `prefers-reduced-motion` disables them for shoppers who request less motion.

## Problem 12 — Audit trail, safety, and finish harness

### Audit trail

FastAPI creates an internal SQLite `audit_events` table at startup and appends the same safe event metadata to [`output/audit_trail.json`](audit_trail.json). The file is JSON Lines: one JSON object per line, opened in append mode, so new runs do not wipe earlier records. Each record has `time`, `tool_name`, short non-sensitive `args`, short `result`, and `stop_reason`.

Events include `chat.completed`, `chat.failed`, and database-tool outcomes. Tool metadata includes counts, limits, sizes, and catalogue IDs—not raw chat text, passwords, hashes, API keys, or email addresses. The audit table and file are internal artifacts and are not exposed as browser endpoints.

### Safety boundary

The agent is read-only. The system prompt treats catalogue fields, page context, and conversation history as data rather than instructions; refuses secrets, credentials, hashes, API keys, and private-user requests; uses database tools for every product fact; labels zero stock as out of stock; and does not claim to place orders or change accounts/inventory. Audit records intentionally exclude passwords, hashes, API keys, raw emails, full prompts, and hidden instructions.

### Final run harness

From the backend folder:

```bash
cd "Homework/HW 4/backend"
uvicorn main:app --reload --port 8000
```

In a second terminal:

```bash
cd "Homework/HW 4/frontend"
npm run dev
```

Verification completed for this problem: backend modules compile, the startup path creates `audit_events` when absent, and the React/Vite production build passes. The existing app check is available at [`output/app_check.html`](app_check.html), with screenshots in `output/app_check_images/`.

### Models, tools, abilities, and limits

`ChatResponse` contains the shopper-facing `reply`, `product_ids` for linking, and structured `product_matches` for cards. `ProductSearchHit` keeps the card fields small—ID, name, type, price, description, and image path. `ProductDetails` adds verified description, colors, price, and size labels. `StockLookupResult` keeps the requested size and exact size-level stock messages, including out-of-stock states. `AuditTrailEvent` defines the safe JSONL event shape.

The agent can search catalogue records, retrieve one product's details, and check inventory. These tools are read-only and use SQLite as the source of truth. Search returns at most 10 matches; chat requests accept at most 12 history items and the agent prompt uses the most recent 10; messages are capped by the API at 2,000 characters. The agent uses `gpt-5.6-luna` through the server-side Portkey client and allows at most two model retries. Passwords are never sent to the agent.

The system prompt enforces prompt-injection resistance, no secret or private-data disclosure, no payment/password handling, no invented product facts or policies, explicit uncertainty, concise answers, and no claims of orders or account/inventory changes. The frontend runs on Vite port 5173; FastAPI runs from `backend/` on port 8000 with the Uvicorn command above.
