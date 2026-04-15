HOW TO USE THIS FOLDER
======================
Drop your property ad image here before the daily workflow runs (7 AM IST).

Supported formats: .jpg  .jpeg  .png

Rules:
- The system picks the MOST RECENTLY MODIFIED image automatically
- You can have multiple images; only the latest one is used each day
- Replace/add a new image any time to change the next day's creative
- File name does not matter (e.g. project_banner.jpg, site_photo.png)

Priority order (if multiple sources are set):
  1. image_hash  in ad_config.json  (Meta-uploaded hash)
  2. image_url   in ad_config.json  (hosted URL)
  3. THIS FOLDER (auto-scan)        <-- default when above are empty
  4. image_path  in ad_config.json  (explicit local path)