import os
import unittest
from unittest.mock import patch

from src.integrations.google_genai import resolve_google_genai_settings


class GoogleGenAIConfigTests(unittest.TestCase):
    def test_developer_api_key_is_used_by_default(self) -> None:
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "dev-key"}, clear=True):
            settings = resolve_google_genai_settings()

        self.assertFalse(settings.vertexai)
        self.assertEqual("dev-key", settings.api_key)
        self.assertIsNone(settings.project)
        self.assertIsNone(settings.location)

    def test_vertex_backend_uses_project_and_defaults_location(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GOOGLE_GENAI_USE_VERTEXAI": "true",
                "GOOGLE_CLOUD_PROJECT": "vertex-project",
            },
            clear=True,
        ):
            settings = resolve_google_genai_settings()

        self.assertTrue(settings.vertexai)
        self.assertEqual("vertex-project", settings.project)
        self.assertIsNone(settings.api_key)
        self.assertEqual("global", settings.location)

    def test_explicit_false_vertex_flag_keeps_developer_backend(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GOOGLE_GENAI_USE_VERTEXAI": "false",
                "GOOGLE_CLOUD_PROJECT": "vertex-project",
                "GOOGLE_API_KEY": "dev-key",
            },
            clear=True,
        ):
            settings = resolve_google_genai_settings()

        self.assertFalse(settings.vertexai)
        self.assertEqual("dev-key", settings.api_key)
        self.assertIsNone(settings.project)

    def test_vertex_backend_uses_explicit_vertex_key_when_set(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GOOGLE_GENAI_USE_VERTEXAI": "true",
                "GOOGLE_CLOUD_PROJECT": "vertex-project",
                "GOOGLE_API_KEY": "old-dev-key",
                "VERTEX_API_KEY": "vertex-key",
            },
            clear=True,
        ):
            settings = resolve_google_genai_settings()

        self.assertTrue(settings.vertexai)
        self.assertEqual("vertex-key", settings.api_key)

    def test_vertex_backend_ignores_google_api_key_without_explicit_vertex_key(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GOOGLE_GENAI_USE_VERTEXAI": "true",
                "GOOGLE_CLOUD_PROJECT": "vertex-project",
                "GOOGLE_API_KEY": "old-dev-key",
            },
            clear=True,
        ):
            settings = resolve_google_genai_settings()

        self.assertTrue(settings.vertexai)
        self.assertIsNone(settings.api_key)

    def test_vertex_backend_requires_project(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GOOGLE_GENAI_USE_VERTEXAI": "true",
                "VERTEX_API_KEY": "vertex-key",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "GOOGLE_CLOUD_PROJECT"):
                resolve_google_genai_settings()


if __name__ == "__main__":
    unittest.main()
