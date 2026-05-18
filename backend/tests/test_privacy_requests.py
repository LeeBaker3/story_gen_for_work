from backend.database import AdminAuditEvent, User


def test_regular_user_can_create_and_list_own_privacy_requests(
    client,
    regular_user_auth_headers,
):
    export_response = client.post(
        "/api/v1/users/me/privacy-requests",
        headers=regular_user_auth_headers,
        json={"request_type": "account_export"},
    )
    assert export_response.status_code == 201
    assert export_response.json()["status"] == "submitted"

    delete_response = client.post(
        "/api/v1/users/me/privacy-requests",
        headers=regular_user_auth_headers,
        json={"request_type": "account_delete"},
    )
    assert delete_response.status_code == 201
    assert delete_response.json()["status"] == "submitted"

    list_response = client.get(
        "/api/v1/users/me/privacy-requests",
        headers=regular_user_auth_headers,
    )
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 2
    assert {item["request_type"] for item in payload} == {
        "account_export",
        "account_delete",
    }


def test_duplicate_open_privacy_request_of_same_type_is_rejected(
    client,
    regular_user_auth_headers,
):
    first_response = client.post(
        "/api/v1/users/me/privacy-requests",
        headers=regular_user_auth_headers,
        json={"request_type": "account_export"},
    )
    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/api/v1/users/me/privacy-requests",
        headers=regular_user_auth_headers,
        json={"request_type": "account_export"},
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {
        "detail": "An open privacy request of this type already exists."
    }


def test_admin_can_list_and_update_privacy_requests(
    client,
    admin_auth_headers,
    regular_user_auth_headers,
    db_session,
):
    create_response = client.post(
        "/api/v1/users/me/privacy-requests",
        headers=regular_user_auth_headers,
        json={"request_type": "account_export"},
    )
    request_id = create_response.json()["id"]

    list_response = client.get(
        "/api/v1/admin/privacy-requests",
        headers=admin_auth_headers,
    )
    assert list_response.status_code == 200
    assert any(item["id"] == request_id for item in list_response.json())

    update_response = client.patch(
        f"/api/v1/admin/privacy-requests/{request_id}",
        headers=admin_auth_headers,
        json={"status": "in_review"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "in_review"

    audit_event = db_session.query(AdminAuditEvent).filter(
        AdminAuditEvent.event_type == "privacy_request_status_change",
        AdminAuditEvent.target_id == request_id,
    ).one()
    assert audit_event.metadata_json == {
        "privacy_request_id": request_id,
        "user_id": update_response.json()["user_id"],
        "request_type": "account_export",
        "old_status": "submitted",
        "new_status": "in_review",
    }


def test_completing_account_delete_request_soft_deletes_user(
    client,
    admin_auth_headers,
    regular_user_auth_headers,
    db_session,
):
    create_response = client.post(
        "/api/v1/users/me/privacy-requests",
        headers=regular_user_auth_headers,
        json={"request_type": "account_delete"},
    )
    request_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/admin/privacy-requests/{request_id}",
        headers=admin_auth_headers,
        json={"status": "completed"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "completed"

    regular_user = db_session.query(User).filter(
        User.username == "user@example.com"
    ).one()
    assert regular_user.is_deleted is True
    assert regular_user.is_active is False
