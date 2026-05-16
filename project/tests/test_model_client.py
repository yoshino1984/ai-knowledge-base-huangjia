from project.pipeline import model_client


def test_create_provider_treats_empty_provider_env_as_default(monkeypatch):
    """LLM_PROVIDER 为空字符串时应回退到 deepseek。"""

    captured = {}

    class FakeProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setenv("LLM_PROVIDER", "")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    monkeypatch.setattr(model_client, "OpenAICompatibleProvider", FakeProvider)

    model_client.create_provider()

    assert captured["provider_name"] == "deepseek"
    assert captured["model"] == "deepseek-chat"
