# Portfolio Project

This is a simple portfolio website made with HTML.

## Files

- `index.html` - Main landing page
- `album.html` - Shared album page for Strasbourg, Catalonia, Andalusia, Corsica, French Alps, Madrid, and Paris
- `Photos/` - Portfolio photo assets

## How to Use

Open `index.html` in your browser to view the main page.

From there, you can navigate to the individual albums.

## Photo Time Data

Album "real time" captions are generated from each source photo's EXIF shutter speed in `Photos/<Album>/`.

Regenerate the data after adding or removing photos:

```bash
python3 scripts/update-photo-time-data.py
```

Or keep it updating while you work:

```bash
python3 scripts/update-photo-time-data.py --watch
```
