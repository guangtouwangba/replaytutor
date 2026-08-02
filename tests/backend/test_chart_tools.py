from fastapi.testclient import TestClient


def test_professional_chart_tool_registry_contains_exactly_forty_tools(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/chart-tools")
    assert response.status_code == 200
    tools = response.json()["tools"]
    assert len(tools) == 40
    assert len({item["tool_id"] for item in tools}) == 40
    assert all(1 <= item["min_anchors"] <= item["max_anchors"] <= 16 for item in tools)


def test_chart_tool_templates_and_preferences_are_persistent(
    client: TestClient,
) -> None:
    created = client.post(
        "/api/v1/chart-tools/templates",
        json={
            "tool": "trend_line",
            "name": "关键趋势",
            "style": {"line_color": "#ffcc00", "line_width": 3, "line_dash": "dashed"},
            "properties": {"show_coordinates": True},
        },
    )
    assert created.status_code == 200
    template = created.json()
    assert template["style"]["line_color"] == "#ffcc00"

    preference = client.put(
        "/api/v1/chart-tools/preferences/trend_line",
        json={
            "favorite": True,
            "recent_rank": 0,
            "continuous": True,
            "default_template_id": template["template_id"],
        },
    )
    assert preference.status_code == 200
    assert preference.json()["favorite"] is True
    assert (
        client.get("/api/v1/chart-tools/templates").json()["templates"][0][
            "template_id"
        ]
        == template["template_id"]
    )
    assert (
        client.get("/api/v1/chart-tools/preferences").json()["preferences"][0]["tool"]
        == "trend_line"
    )

    deleted = client.delete(f"/api/v1/chart-tools/templates/{template['template_id']}")
    assert deleted.status_code == 204
    assert client.get("/api/v1/chart-tools/templates").json()["templates"] == []
