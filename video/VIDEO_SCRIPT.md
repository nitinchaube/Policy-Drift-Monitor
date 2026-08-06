# Video script

Five minutes hard maximum. The prompt grades vocal delivery and professional visual
presence, not just content, so the words below are written to be spoken, not read.

Total written time is about 4:40, which leaves room to breathe. If you run long, cut the
scale section (3:55) first and the limitations line second. Never cut the C-007 moment.

## Before you record

- Camera at eye level, window or lamp in front of you, not behind.
- Test audio. Bad audio reads as unprofessional faster than anything else on screen.
- Have both servers already running and the app already loaded on the Policy Studio tab.
  Do not start a server on camera.
- Have the deck open in presenter view on a second display, or just know the beats.
- Do one full rehearsal out loud with a timer before the take that counts.
- Two or three takes. The third is usually the one.

---

## 0:00 – 0:30 · On camera, no screenshare

> Hi, I'm Nitin Chaube. For the Cotiviti assessment I chose topic three, content
> management in health care, and specifically the part of it that turns written policy
> into executable rules.
>
> Here's the problem in one sentence. A health plan reads a coverage policy, writes claim
> rules from it, and puts those rules into production. Then the policy gets revised. The
> rules don't. And nobody's job is to go back and check.
>
> I built a tool that finds those stale rules, and I ran it on real Medicare documents.

**Cue:** stay on camera. Do not rush this. It sets the tone.

---

## 0:30 – 1:00 · Slide 2, the four-panel timeline

> In January an analyst reads the policy and writes twelve rules. They go live and they're
> correct. In July, CMS revises the policy. Three coverage criteria change. Nobody re-reads
> the rule library, so from August those rules are quietly denying claims the policy now
> covers.
>
> The rule wasn't written badly. It was right when it was written. The failure is that
> nothing revisits it.

---

## 1:00 – 1:35 · Slide 4, the three documented changes

> This is the actual document pair. Medicare LCD L33822, the version effective January 2020
> and the revision effective July 2021.
>
> CMS publishes a revision history inside the document, so it tells you what changed. That's
> my answer key, which matters, because it means the evaluation set wasn't written by me.
> Three coverage changes. And a fourth row, which is a trap: the criteria list got renumbered,
> so a sentence changed without the requirement changing at all.

---

## 1:35 – 2:25 · Screenshare, Policy Studio

**Cue:** app already open on Policy Studio, Model view.

> Here's the tool. On the left is the real policy text, straight out of the CMS PDF. On the
> right are the rules a language model extracted from it.
>
> [click the BGM testing rule]
>
> When I select a rule, it highlights the sentence it came from. And that link is verified,
> not trusted. The model quotes a sentence, and then my code goes and finds that quote in the
> document. If it can't find it, the citation is fabricated and the rule gets thrown away.
>
> [switch to v2]
>
> Now here's version two. That sentence is gone. Medicare deleted the requirement.

---

## 2:25 – 3:05 · Screenshare, Claims tab

> The rules compile to Python and decide claims. No model anywhere in the decision path,
> because a denial has to be reproducible and defensible three years later on appeal.
>
> [expand C-007]
>
> Claim C-007 was denied. Here's every rule that was evaluated, the one that failed, and
> the exact policy sentence behind it. And this paragraph is what the provider would
> actually receive: what failed, quoting the policy, and what to do next.
>
> This claim was denied for testing blood glucose once a day, under a requirement Medicare
> removed in July 2021.

---

## 3:05 – 3:55 · Screenshare, Drift tab

> This is the part that matters. Rather than extracting rules from both versions and
> diffing them, which just fills up with the model's own randomness, I hold the ruleset
> fixed and ask one narrow question about each rule.
>
> And the model doesn't give me the verdict. It reports three observations, and the verdict
> comes from a decision table in code. That's deterministic and I can inspect it.
>
> [point at the table]
>
> One rule contradicted, retire it. One modified, a human needs to rewrite it. The rest
> supported. Including this one, which is the renumbering trap. The sentence changed, the
> requirement didn't, and it correctly says supported.
>
> [scroll to flips]
>
> Re-running the same twenty claims, six change decision, and one thousand two hundred
> dollars was being wrongly withheld.

---

## 3:55 – 4:25 · Scorecard tab

> Scored against CMS's own revision history: all three documented changes caught, zero false
> alarms, and the trap passed.
>
> I also ran a negative control, two consecutive official versions from 2024 where nothing
> substantive changed. Zero findings, and it worked that out before spending a single model
> call, which is the whole cost argument at scale.
>
> And the tool still fails its own quality gate on two rules. That's on the screen rather
> than hidden, because a tool that hides its own defects is worse than no tool.

---

## 4:25 – 4:50 · Back on camera

> If I were recommending one thing to Cotiviti, it wouldn't be an authoring product. It
> would be regression monitoring over the edit library that already exists: watch the source
> documents, and return a ranked list of edits a revision has invalidated, priced by
> replaying recent claims. It replaces nothing and it fails safe.
>
> This runs on one policy and four documents. What it proves is that the mechanism works.
> It doesn't prove it generalises, and I've written down what would have to be true for that.
>
> Thanks for your time.

---

## Things to say only if asked, not in the video

- Round-trip verification: decompile a rule back to English without showing the model the
  source, then compare. It found the dropped pump criterion with no answer key at all.
- Why the gate fails: one rule encodes a per-30-day limit the claim schema can't express.
  The schema is the real bottleneck, not the model.
- Why majority voting alone didn't work: the model was wrong the same way across runs, so
  the plurality was wrong. Voting fixes noise, not bias.

## Do not

- Do not read these words off the screen. Know the beats and speak them.
- Do not apologise for the limitations section. Deliver it flat and confident.
- Do not run over five minutes. They said five.
