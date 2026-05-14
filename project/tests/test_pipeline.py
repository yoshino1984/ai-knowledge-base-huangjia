import json

from project.pipeline import pipeline


def test_step_organize_skips_index_json_when_loading_existing_articles(tmp_path, monkeypatch):
    articles_dir = tmp_path / "articles"
    articles_dir.mkdir()
    (articles_dir / "index.json").write_text(
        json.dumps([{"id": "index-entry", "title": "index only"}]),
        encoding="utf-8",
    )
    (articles_dir / "existing.json").write_text(
        json.dumps({"source_url": "https://example.com/existing"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(pipeline, "ARTICLES_DIR", articles_dir)

    organized = pipeline.step_organize(
        [
            {
                "id": "2026-05-15-github-new",
                "title": "new item",
                "source": "github",
                "source_url": "https://example.com/new",
                "summary": "new summary",
                "score": 8,
                "tags": ["AI"],
            },
            {
                "id": "2026-05-15-github-existing",
                "title": "existing item",
                "source": "github",
                "source_url": "https://example.com/existing",
                "summary": "existing summary",
                "score": 8,
                "tags": ["AI"],
            },
        ]
    )

    assert [item["source_url"] for item in organized] == ["https://example.com/new"]
