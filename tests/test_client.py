import pytest
from datetime import date, timedelta
from uuid import UUID, uuid4

from client.client import Client
from enums.enums import ClientStatus


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def born_years_ago(years: int, day_shift: int = 0) -> date:
    """
    Дата рождения, сдвинутая на `day_shift` дней относительно "ровно `years` лет назад".

    Семантика day_shift:
      day_shift == 0   — ДР сегодня, человеку ровно `years` лет;
      day_shift <  0   — ДР уже был в этом году, возраст = `years`;
      day_shift >  0   — ДР ещё впереди в этом году, возраст = `years - 1`.
    """
    today = date.today()
    try:
        d = today.replace(year=today.year - years)
    except ValueError:  # 29 февраля в невисокосный год
        d = today.replace(year=today.year - years, day=28)
    return d + timedelta(days=day_shift)


# ---------------------------------------------------------------------------
# 1. Тип birth_date
# ---------------------------------------------------------------------------

def test_birth_date_as_string_raises(make_client):
    with pytest.raises(ValueError, match="date"):
        make_client(birth_date="1990-01-01")


def test_birth_date_as_none_raises(make_client):
    with pytest.raises(ValueError):
        make_client(birth_date=None)


@pytest.mark.parametrize("bad_value", ["1990-01-01", 0, 12345, object(), [2020, 1, 1]])
def test_birth_date_as_wrong_type_raises(bad_value, make_client):
    with pytest.raises(ValueError):
        make_client(birth_date=bad_value)


# ---------------------------------------------------------------------------
# 2. Возраст — свойство age
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("years,day_shift,expected_age", [
    # day_shift == 0 — ДР сегодня
    (18, 0, 18),
    (19, 0, 19),
    (25, 0, 25),
    (100, 0, 100),
    # day_shift < 0 — ДР уже был в этом году, возраст = years
    (18, -1, 18),       # вчера исполнилось 18
    (18, -300, 18),     # ДР был давно в этом году
    (30, -100, 30),     # ДР был ~100 дней назад
    # day_shift > 0 — ДР ещё впереди, возраст = years - 1
    (30, 100, 29),      # ДР будет через ~100 дней → ещё 29
])
def test_age_property_returns_expected(years, day_shift, expected_age, make_client):
    client = make_client(birth_date=born_years_ago(years, day_shift))
    assert client.age == expected_age


def test_age_is_recomputed_each_access(make_client):
    """age — это @property, а не поле: значение не кэшируется."""
    client = make_client(birth_date=born_years_ago(25))
    assert client.age == client.age == 25


# ---------------------------------------------------------------------------
# 3. Граничные случаи возраста вокруг 18
# ---------------------------------------------------------------------------

def test_age_17_full_years_raises(make_client):
    with pytest.raises(ValueError, match="18"):
        make_client(birth_date=born_years_ago(17))


def test_age_17_birthday_tomorrow_raises(make_client):
    # ДР будет завтра → сегодня ещё 17
    with pytest.raises(ValueError):
        make_client(birth_date=born_years_ago(18, day_shift=1))


def test_age_17_almost_18_raises(make_client):
    with pytest.raises(ValueError):
        make_client(birth_date=born_years_ago(18, day_shift=30))


def test_age_18_today_ok(make_client):
    client = make_client(birth_date=born_years_ago(18))
    assert client.age == 18


def test_age_18_birthday_yesterday_ok(make_client):
    client = make_client(birth_date=born_years_ago(18, day_shift=-1))
    assert client.age == 18


def test_future_birth_date_raises(make_client):
    with pytest.raises(ValueError):
        make_client(birth_date=date.today() + timedelta(days=365))


def test_child_of_newborn_raises(make_client):
    with pytest.raises(ValueError):
        make_client(birth_date=date.today() - timedelta(days=1))


# ---------------------------------------------------------------------------
# 4. UUID
# ---------------------------------------------------------------------------

def test_default_id_is_uuid_instance(make_client):
    client = make_client()
    assert isinstance(client.id, UUID)


def test_two_clients_get_different_uuids(make_client):
    c1 = make_client()
    c2 = make_client()
    assert c1.id != c2.id


def test_many_clients_get_unique_uuids(make_client):
    ids = {make_client().id for _ in range(500)}
    assert len(ids) == 500


def test_explicit_id_is_kept(make_client):
    fixed = uuid4()
    client = make_client(id=fixed)
    assert client.id == fixed


def test_uuid4_default_factory_not_shared_between_instances(make_client):
    """Регрессия: uuid4() должен вызываться для каждого экземпляра, а не один раз при импорте."""
    clients = [make_client() for _ in range(10)]
    assert len({c.id for c in clients}) == 10


# ---------------------------------------------------------------------------
# 5. Сохранение полей
# ---------------------------------------------------------------------------

def test_all_fields_are_stored():
    bd = born_years_ago(30)
    accounts = [uuid4(), uuid4()]
    status = next(iter(ClientStatus))
    client = Client(
        status=status,
        name="Пётр Петров",
        birth_date=bd,
        phone="+79991234567",
        email="petr@example.com",
        pin_code="1234",
        accounts=accounts,
    )
    assert client.status == status
    assert client.name == "Пётр Петров"
    assert client.birth_date == bd
    assert client.phone == "+79991234567"
    assert client.email == "petr@example.com"
    assert client.accounts == accounts


def test_accounts_default_not_shared(make_client):
    c1 = make_client()
    c2 = make_client()

    c1.accounts.append(uuid4())

    assert c1.accounts != c2.accounts
    assert c2.accounts == []


def test_default_status_is_active(make_client):
    client = make_client()
    assert client.status == ClientStatus.ACTIVE


def test_invalid_status_raises(make_client):
    with pytest.raises(ValueError):
        make_client(status="ACTIVE")


def test_invalid_id_raises(make_client):
    with pytest.raises(ValueError):
        make_client(id="12345")

def test_invalid_accounts_type_raises(make_client):
    with pytest.raises(ValueError):
        make_client(accounts="not a list")


def test_accounts_must_contain_uuids(make_client):
    with pytest.raises(ValueError):
        make_client(accounts=["12345"])