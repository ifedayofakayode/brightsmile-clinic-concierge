# Runbook: if X breaks, check Y

One page for whoever operates Clinic Concierge. Start with the **Executions** tab of the affected n8n workflow: it shows every run, every node's input and output, and the exact error.

## 1. Quick triage (60 seconds)

1. Is workflow `01 Clinic Concierge: Main` **Active**?
2. Did a new execution appear when you sent a message? **No** means the gateway is not reaching n8n. **Yes, with a red node** means open that node and read the error.
3. Check the `Errors` table in Airtable and the Telegram alert for the same time.
4. Search `Message_log` for the customer's phone number to see what the bot received and sent, with the `tool_used` and `guard_result` for each reply.

## 2. Symptoms

| Symptom | Likely cause | Check | Fix |
|---|---|---|---|
| Bot never replies | Workflow inactive, or gateway not calling n8n | Executions tab. Gateway dashboard: webhook URL and delivery log. `WEBHOOK_URL` setting on self-hosted n8n | Activate the workflow. Re-save the trigger. Make sure n8n is reachable over public HTTPS |
| Bot replies twice | Dedupe lookup failing, or two active copies of the workflow | `Check Duplicate` node and its formula. Workflows list for duplicates | Fix the formula (single `=` for an expression), turn on Always Output Data, deactivate the extra copy |
| Workflow stops after a lookup, no reply | An Airtable search found nothing and n8n stopped | The last green node. Settings tab of that node | Turn on **Always Output Data** for searches that can legitimately return nothing |
| Bot answers "I am not sure I understood" to everything | AI step failing validation, or wrong output path | `Classify Intent` output vs the path read in `Validate AI JSON` | Adjust the path to the AI text. Confirm JSON output is on and the API key has credit |
| Reply is "Okay, we start over" for a normal message | Reset key logic wrong in `Simple Replies` | The `key` line in the code | Use the route-based check: `reset` only when the route is `reset` |
| "Node has not been executed" in a Code node | The code reads a node that is not on this path | Node names in the error | Read context from a node that always runs (for example `Build Context`). Node names are case-sensitive |
| Numbered reply ("1", "2") does nothing | State not saved or not read | `Conversations` row: `state` and `pending_slots`. `Build Context` output | Fix the Save State node (match on `conv_id`). Make sure columns are read from `fields` if Airtable nests them |
| No time slots offered | Calendar or held-slots search returned nothing and stopped, or hours/duration wrong | `Get Held Slots` settings. `Make Slots` output | Always Output Data and Execute Once on the held-slots search. Check opening hours and `duration_min` |
| Times are off by an hour | Missing time zone | Workflow timezone. ISO strings with offsets. Code uses `America/Chicago` | Set the workflow timezone and keep offsets in stored times |
| Wrong or missing price | `Services` row inactive, unverified, or typo | `Services` table: `active`, `price_usd`, `last_verified` | Correct the row and set a fresh `last_verified`. The bot reads it immediately |
| Reply replaced by a fallback and `guard_result` starts with `blocked` | The output guard did its job | `Message_log.guard_result` and the logged original text | Fix the node that produced the bad text, or add the new legitimate amount to the table |
| Payment link not sent | Stripe request failed | `Create Stripe checkout` node: key, body fields | Use a test-mode secret key. Body must be form-urlencoded with `metadata[appointment_record_id]` |
| Paid, but no confirmation | Payment webhook workflow inactive or not registered | Workflow `02` Active. Stripe Developers, Webhooks, delivery attempts | Activate it. Confirm Stripe is in the same mode (test or live) as the key |
| Customer paid after the hold expired | Expected edge case | Workflow `02`, false branch. Alert on the team channel | Contact the customer, rebook, or refund in Stripe. Mark the appointment `needs_review` |
| Held slot never reopens | Workflow `03 Expire Holds` inactive | Executions for `03` | Activate it. Check the 5-minute schedule |
| Calendar node errors | Google token expired or consent screen in testing mode | Credential status in n8n | Reconnect the Google credential. Add the account as a test user, or publish the consent screen |
| WhatsApp send fails | Gateway device disconnected, wrong number format, or outside the 24-hour window | Gateway dashboard. Phone format with country code. Time of the last customer message | Reconnect the device. Fix the number. Use an approved template outside the window |
| Bot ignores one customer | `human_takeover` is ticked for that chat | `Conversations.human_takeover` | Untick it to resume the bot |

## 3. Routine operations

| Task | How |
|---|---|
| Change a price or deposit | Edit the row in `Services` and set `last_verified` to today |
| Add or edit an FAQ | Edit `Knowledge_base`: fill both languages and keep `active` ticked |
| Pause the bot for one customer | Tick `human_takeover` on their `Conversations` row |
| Pause the whole bot | Deactivate workflow `01` |
| Rotate a key | Create the new key, update the credential in n8n, run one test message, then revoke the old key |
| Delete a customer's data on request | Delete their rows in `Conversations`, `Leads`, `Message_log` and `Appointments`, then confirm |
| Review blocked replies | Filter `Message_log` where `guard_result` starts with `blocked` |

## 4. Escalation

1. Run the quick triage above.
2. Fix configuration problems (credentials, inactive workflows, table values) yourself.
3. For anything involving payments received but not booked, contact the customer the same day.
4. If the cause is not obvious, collect: the execution link, the failing node's name, its error text, the customer's phone number (last digits only in any public channel) and the time. Never paste keys or tokens when asking for help.
