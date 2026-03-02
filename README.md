# tyler dev

Personal blog source for `vwtyler.dev`, built with Jekyll + the Chirpy theme and deployed with GitHub Pages.

This blog focuses on:

- community radio engineering work (KAAD-LP / kaad-one)
- homelab infrastructure, automation, and reliability notes

## Stack

- Jekyll (Ruby)
- Chirpy theme (`jekyll-theme-chirpy`)
- GitHub Actions for build/deploy
- GitHub Pages hosting

## Writing workflow

- Draft posts in `_drafts/`
- Publish posts in `_posts/` using `YYYY-MM-DD-title.md`
- Use front matter with `title`, `date`, `categories`, and `tags`

Current categories in use:

- `kaad-one`
- `homelab`

## Deploy workflow

Push to `main` triggers GitHub Actions (`Build and Deploy`) and publishes to Pages.

Domain configuration for production is:

- `_config.yml` `url: https://vwtyler.dev`
- root `CNAME` file with `vwtyler.dev`

## Notes

- Secrets (tokens, keys, `.env`) are never committed.
- Posts may include sanitized configs/commands from production systems.
