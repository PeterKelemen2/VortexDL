from app.schemas.role import RoleRead


class DummyRole:
    def __init__(self, id, name, description=None):
        self.id = id
        self.name = name
        self.description = description


def test_role_read_model_from_attributes():
    dummy = DummyRole(id=1, name="user", description="Default role")
    role = RoleRead.model_validate(dummy)

    assert role.id == 1
    assert role.name == "user"
    assert role.description == "Default role"


def test_role_read_model_from_attributes_omits_none_description():
    dummy = DummyRole(id=2, name="admin")
    role = RoleRead.model_validate(dummy)

    assert role.id == 2
    assert role.name == "admin"
    assert role.description is None
