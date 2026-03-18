import pytest
import sqlite3
import uuid
from backend.database.sqlite_db import get_db_connection
from backend.database import admin

def test_delete_empty_group():
    # Setup
    group_name = f"Test Empty Group {uuid.uuid4()}"
    group_id = admin.create_group(group_name)
    
    # Action
    admin.delete_group(group_id)
    
    # Verify
    groups = admin.list_groups()
    assert not any(g['id'] == group_id for g in groups)

def test_delete_group_with_members_fails():
    # Setup
    group_name = f"Test Group With Members {uuid.uuid4()}"
    group_id = admin.create_group(group_name)
    
    # We need a user to add to the group. Let's create a dummy user
    from backend.database import auth
    username = f"dummy_{uuid.uuid4()}"
    user = auth.create_user(username, "password123")
    
    admin.add_user_to_group(group_id, user['id'])
    
    # Action & Verify
    with pytest.raises(ValueError, match="Cannot delete a group that currently has members."):
        admin.delete_group(group_id)
        
    # Verify group still exists
    groups = admin.list_groups()
    assert any(g['id'] == group_id for g in groups)
