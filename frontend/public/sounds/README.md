# POS sound assets

Two cues shipped with the till. Both are served from this directory by Next.js and
fetched once by the register (`preloadSounds()`), then decoded into memory.

| File | Cue | Played for |
|---|---|---|
| `store-scanner-beep.mp3` | Scanner beep | Product added, barcode scan matched, quantity increased |
| `cash-register-kaching.mp3` | Kaching | A completed sale only — never for a cart addition |

The error (blocked add / out of stock) and removal cues are synthesized in
`src/lib/pos/sounds.ts`; no assets were supplied for those, so nothing here replaces
or imitates the scanner beep.

## Licence record

Fill this in when the files are added — it must be complete before the app ships.

### store-scanner-beep.mp3

- **Title:** Store Scanner Beep
- **Author / uploader:** zerolagtime (Freesound), uploaded via freesound_community
- **Source:** https://pixabay.com/sound-effects/film-special-effects-store-scanner-beep-90395/
- **Licence:** Pixabay Content Licence (verify on the asset page at download time)
- **Downloaded:** _pending_

### cash-register-kaching.mp3

- **Title:** Cash Register (Kaching) - Sound Effect
- **Author / uploader:** _pending_
- **Source:** _pending_
- **Licence:** _pending_
- **Downloaded:** _pending_

## Licence notes

Pixabay's Content Licence permits free commercial and non-commercial use with no
attribution required, but the asset must not be redistributed on its own or sold
unaltered. Bundling it inside this application is permitted. The store scanner beep
originates from Freesound — if the Freesound original carries a different licence
(for example CC-BY), record the credit required by that licence here.
