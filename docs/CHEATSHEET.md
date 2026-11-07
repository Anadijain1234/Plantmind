# Ustaad — cheat sheet (explain it in your own words)

**One line:** When your best expert leaves, their know-how shouldn't. Ustaad remembers what the senior people did and whether it worked, gives it to the next person at the right moment, and gets better every time someone taps *worked* or *didn't work*.

**The analogy:** A new cricketer has a senior player standing next to him who remembers every match: "last time this bowler did this, this shot worked, that one got me out." Ustaad is that senior for a factory, kitchen, hospital, garage or IT team.

---

## The 3 flows you must be able to explain

**1. How a memory is saved**
A worker says or types what happened ("CNC-3 whistling, realigned the coupling, fixed in 40 minutes"). The AI turns it into a clean record: machine, problem, cause, action, result. It is saved twice:
- into **Hindsight**, the memory that understands meaning and can search it;
- into a small local database (the "scorebook") that keeps exact numbers for charts.

It shows as **Unreviewed** until a senior approves it.

**2. How an answer is made**
1. A worker asks a question.
2. **Hindsight recall** searches the memory twice: once near this machine and its twins, and once across the whole industry.
3. **A second check** re-ranks the results. Memories that share the alarm code or the same words go to the top. "Same machine, different problem" memories drop.
4. **Groq** (the AI) gets those memories and must first say which ones are about the *same* problem. Then it writes the answer: check first, the steps, what NOT to repeat, who did it and when.
5. The green or orange banner counts only the memories it actually used.

If nothing matches, it says honestly: "New problem — nothing in your team's memory."

This is RAG. Hindsight is the "look things up" part and Groq is the "write the answer" part.

**3. How it learns**
After the fix the worker taps **✔ Worked** or **✖ Didn't work**. That result becomes a new memory.
- Fixes that keep working rise and get the **Verified** tag.
- Fixes that failed show up in "Don't repeat".
- The expert whose fix was reused gets credit on their **skill passport**.
- If it didn't work, Ustaad says who to call and opens WhatsApp with the message ready.

---

## Every feature in one line

| Feature | One line |
|---|---|
| Ask Ustaad | Describe a problem by typing, voice or photo, and get your team's proven fix with who did it and when. |
| Memory ON / OFF | OFF is a normal chatbot; ON is your team's real history. This shows why memory matters. |
| Trust tags | ✔ Verified (worked 2+ times), Tested once, Unreviewed, ✖ Didn't work, Public record, 📘 Maker's manual, 🧠 Hindsight pattern, 📡 Sensor-confirmed. |
| Not sure which machine | The worker doesn't have to pick one; Ustaad searches everything. |
| I fixed something | Say what you did in any language; it becomes a memory. |
| Approvals | A senior checks new knowledge before it counts as trusted. |
| Flag as wrong | A bad memory gets flagged and Ustaad stops using it. |
| Translate / Listen | Hindi, Kannada, Hinglish (Sarvam); 🔊 reads the answer aloud. |
| **My machines** | Every machine in one place, with a health light, service due, spare parts, warranty, history, experts and manual. |
| Add from manual / website / nameplate | Upload the maker's PDF, paste its web page or snap the nameplate, and the AI fills the form. |
| Manual says vs team found | The answer shows when the team's real fix differs from the official manual. |
| QR sticker | Like a DMart barcode: stick it on the machine, scan it with a phone, and Ustaad opens with that machine picked. |
| Service due | "Coupling spider: 4 days overdue". The last replacement date comes from the repair history. |
| Spare parts | "0 in store, order now" shows in answers; replacing a part in a log reduces the stock. |
| Sensor auto-log | A sensor crosses its limit, so Ustaad writes half the log itself; normal readings after the fix mean "Sensor-confirmed". |
| Ask the expert | A fix failed, so Ustaad names who fixed it before and drafts a WhatsApp message. |
| SOP / playbook | A printable procedure built only from fixes that worked. |
| Risk radar | "If Ramesh leaves, these fixes leave with him." |
| Exit interview | Questions for a leaving expert, only about things nobody wrote down. |
| Skill passport | Proof of a person's skills, built from fixes that worked. |
| Shift report | A handover note from real records, sensor alerts and out-of-stock parts. |
| ROI dashboard | Downtime hours saved, repeat failures avoided, fixed vs failed, ₹ saved, before vs after. |
| Knowledge coverage | Each machine scored /100 for how much of its know-how is captured; red flag when only one person knows it. |
| Expert leaderboard | Points for fixes that worked and fixes others reused, plus badges. Credit drives sharing. |
| Quiz | New joiners learn from the team's own past problems. |
| Failure prediction | A model trained on Microsoft's public 100-machine data says *when*; Ustaad's memory says *what to do*. |
| Build your own industry | Type "bakery" and Ustaad creates the roles and equipment; memory starts empty and learns. |
| 💾 Auto-save | Everything added on the site is saved to our GitHub repo and comes back after a restart or redeploy. |
| Off-topic guard | "Capital of France?" or a medicine dose gets "Outside what Ustaad answers". |

---

## Questions a judge may ask

- **What is Hindsight?** An agent-memory service by Vectorize. We use its 4 calls:
  - `create_bank`: one memory bank per industry;
  - `retain`: save a memory;
  - `recall`: search memories by meaning;
  - `reflect`: reason over many memories, used to build SOPs.

  It also learns **patterns** by itself, which we show as "🧠 Pattern Hindsight learned".
- **Why two stores (Hindsight + SQLite)?** Hindsight understands and searches meaning. SQLite keeps exact numbers for charts, trust counts, approvals and stock. It's like a brain plus a notebook.
- **Doesn't free hosting lose data on every deploy?** Knowledge is safe in Hindsight. The notebook part (machines, stock, approvals) is **auto-saved** a few seconds after every change to one file on a separate branch of our GitHub repo, and loaded back when the server starts (the 💾 chip). If GitHub can't be reached at start, saving pauses, so good data is never overwritten.
- **Is the data real?** The people and companies are fictional. The facts and public data are real:
  - FDA device reports, NHTSA car complaints, NYC kitchen inspections, Zomato reviews;
  - 240 public outage write-ups, Microsoft and AI4I machine datasets;
  - real maker manuals.

  Spare-part stock and warranty dates are demo data, and they are marked as demo on screen.
- **The model scores AUC 1.0. Is that cheating?** No. Microsoft generated that dataset for a tutorial, so its signals are cleaner than any real plant. We checked for data leakage (none found), and we say this on screen.
- **Is it heavy?** No. Our server is a small Flask app. Hindsight (memory) and Groq/Sarvam (AI) are services, so each question makes about 3 API calls. If Groq fails, Sarvam takes over. If both fail, a rule-based answer still works.
- **How does it scale?** A new company is a new Hindsight bank. A new industry is one JSON file. The server keeps no state between requests, so you can run more copies. For real customers, move SQLite to Postgres.
- **What's next?** Offline mode for low-network shop floors, a WhatsApp bot, and a quiz from a new machine's manual.
