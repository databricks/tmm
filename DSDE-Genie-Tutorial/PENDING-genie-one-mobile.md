# PENDING: Genie One on mobile module (not yet published)

**Status:** open, staged 2026-09-28 · **Target publish:** ~2026-10-05 (any time works)
**Where it lives:** remote branch `genie-one-mobile` on `databricks/tmm`.
`main` (and the live GitHub Pages site) still has the 8-step tutorial with no mobile module.

Delete this file and the "One-off exception" note in `CLAUDE.md` in the publish commit.

## Which branch am I on? Where does a change go?

```bash
git -C ~/tmm branch --show-current     # main  or  genie-one-mobile
```

| You want… | Branch | Goes live? |
|---|---|---|
| A fix that should be public **now** (typo, other modules) | `main`, then push | Yes, on push (GitHub Pages deploys from `main`) |
| A change to the mobile module or its renumbering | `genie-one-mobile`, then push | No. Only on GitHub as a branch; the site is untouched |

**Words to tell Claude:**
- **"→ main"** or **"publish now"**: commit to `main` and push; it goes live.
- **"→ mobile"** or **"hold for mobile"**: commit to `genie-one-mobile` and push the branch; it stays off the site.
- **"publish mobile"**: run the publish steps below.
- No keyword: Claude asks before committing.

A fix made on `main` this week is picked up automatically by the rebase on publish day.

## What's in the branch

- New page `docs/55-mobile.md` ("6. Databricks Genie One on mobile") + 3 screenshots `docs/assets/55-mobile-*.png`.
- Renumbering: App 6→7, OpenSharing 7→8, Wrap-up 8→9 (H1s, `mkdocs.yml` nav, README agenda/TL;DR, `docs/index.md`, wrap-up recap, prev/next links, `code/app` + `code/opensharing` README titles).
- `CHANGELOG.md` entry and `CLAUDE.md` updates.

## Before publishing (checklist)

- [ ] Confirm the Genie mobile app works on **Databricks Free Edition** (the tutorial promises Free Edition start to finish). If it does, add one line to the NOTE in `55-mobile.md`; if not, call out the limit.
- [ ] Optional: if the app shows the generated SQL, you can mention it in the recap again.
- [ ] Bump the `Updated` footer dates on touched pages to the publish date.
- [ ] Build check: `cd ~/tmm/DSDE-Genie-Tutorial && mkdocs build -d /tmp/site-check` (one pre-existing `../README.md` warning is OK).

## Publish (copy-paste)

```bash
cd ~/tmm
git fetch origin
git switch genie-one-mobile
git pull
git rebase origin/main                 # picks up this week's fixes from main
git rm DSDE-Genie-Tutorial/PENDING-genie-one-mobile.md
# also remove the "One-off exception" note in DSDE-Genie-Tutorial/CLAUDE.md, bump footer dates
git commit -am "Publish Genie One on mobile module"
git push --force-with-lease            # branch history changed by the rebase

git switch main
git pull
git merge --ff-only genie-one-mobile
git push                               # goes live
git branch -d genie-one-mobile
git push origin --delete genie-one-mobile
rm -f DSDE-Genie-Tutorial/PENDING-mobile-LOCAL.md       # local-only pointer on main
```

## Check status any time

```bash
git -C ~/tmm fetch origin
git -C ~/tmm log --oneline origin/main..origin/genie-one-mobile   # commits waiting to publish
```

## Rollback / abandon

Nothing on `main` depends on the branch. To drop the module: `git push origin --delete genie-one-mobile && git branch -D genie-one-mobile`.
