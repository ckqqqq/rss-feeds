# Chinese RSS titles

Only titles are translated. Never send article bodies or summaries to a language model for this flow.

```sh
uv run --extra translation python feed_generators/translate_rss_titles.py \
  --article ../keqi-blog-content/articles/2026-10-26-把AI文章收进自己的RSS.md \
  --output ../keqi-blog-content/references/rss-translations/titles.json
```

Default: local CTranslate2 int8 CPU inference with the Argos English→Chinese 1.9 OPUS-MT model. No paid API or model tokens. A ~71 MB model downloads once to ignored `.cache/translation/`, with a pinned SHA-256 check. Successful title translations are cached individually and reused when the English title is unchanged. English originals, URLs and optional reviewed Chinese titles stay in the private content repository.

`--engine mymemory` is an optional remote machine translation fallback; it sends only public titles and respects service errors/quotas. Earlier cached titles may come from that service. No automatic fallback incurs API costs. Missing dependencies fail with a clear import error; use `--extra translation`.

Model attribution: English–Chinese Argos 1.9 packages an OPUS-MT model by Jörg Tiedemann and Santhosh Thottingal, *OPUS-MT — Building open translation services for the World*, EAMT 2020, CC-BY 4.0. The package README is preserved inside the cached model. [Argos Translate](https://github.com/argosopentech/argos-translate), [official package index](https://github.com/argosopentech/argospm-index).
