from scripts.configure_local import configure
from scripts.reset_password import reset_password
from app.core.security import verify_password


def test_local_configuration_never_overwrites_existing_file(tmp_path):
    (tmp_path / ".env.example").write_text("SECRET_KEY=\nSERVICE_SECRET=\nGEMINI_API_KEY=\n")
    assert configure(tmp_path)
    content = (tmp_path / ".env").read_text()
    values = dict(line.split("=", 1) for line in content.splitlines())
    assert len(values["SECRET_KEY"]) >= 32
    assert values["SECRET_KEY"] != values["SERVICE_SECRET"]
    assert not configure(tmp_path)
    assert (tmp_path / ".env").read_text() == content


def test_existing_hash_can_be_reset_without_plaintext_or_fake_migration(db, owner, session_factory):
    owner.hashed_password = "legacy-unsupported-hash"
    db.commit()
    reset_password(owner.email, "a-new-test-password-long", session_factory)
    db.refresh(owner)
    assert verify_password("a-new-test-password-long", owner.hashed_password)
    assert owner.token_version == 1
