import pytest

from babylon.engine.hydration.reference import hydrate_industry_hyperedges
from babylon.models.entities.industry import IndustryHyperedge


class MockResult:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class MockScalarResult:
    def __init__(self, data):
        self._data = data

    def all(self):
        return self._data

    def scalar_one_or_none(self):
        return self._data[0] if self._data else None

    def scalars(self):
        return self


class MockSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, query):
        qs = str(query).lower()
        if "dim_county" in qs:
            return MockScalarResult([MockResult(county_id=1)])
        elif "dim_time" in qs:
            return MockScalarResult([MockResult(time_id=27)])
        elif "fact_qcew_annual" in qs:
            return MockScalarResult(
                [
                    MockResult(
                        naics_code="62", industry_title="Health Care", emp=1000, wages=50000.0
                    ),
                    MockResult(
                        naics_code="31-33",
                        industry_title="Manufacturing",
                        emp=2000,
                        wages=100000.0,
                    ),
                ]
            )
        return MockScalarResult([])


class MockDeptMapper:
    @classmethod
    def from_yaml(cls, _path):
        return cls()

    def get_allocation(self, code):
        class Alloc:
            def to_dict(self):
                return {"dept_I": 0.5, "dept_IIa": 0.5, "dept_IIb": 0.0, "dept_III": 0.0}

        return Alloc()

    def get_sector_cv_ratio(self, code):
        return 2.0

    def get_sector_sv_ratio(self, code):
        return 1.0

    def get_profit_rate(self, code):
        return 0.15


@pytest.mark.integration
def test_hydrate_industry_hyperedges_empty(monkeypatch):
    """Test standard empty or failure behavior without an actual DB connection."""
    industries = hydrate_industry_hyperedges([])
    assert isinstance(industries, dict)
    assert len(industries) == 0


@pytest.mark.integration
def test_hydrate_industry_hyperedges_with_data(monkeypatch):
    """Test hydration with mocked SQLite data returning valid industry info."""
    # Mock the session factory
    monkeypatch.setattr("babylon.reference.database.get_reference_session", lambda: MockSession())

    monkeypatch.setattr("babylon.economics.department_mapper.DepartmentMapper", MockDeptMapper)

    industries = hydrate_industry_hyperedges(["26163"])

    assert len(industries) == 2
    assert "ind_62" in industries
    assert "ind_31-33" in industries

    ind_62 = industries["ind_62"]
    assert ind_62.naics_2digit == "62"
    assert ind_62.naics_label == "Health Care"
    assert ind_62.total_employment == 1000
    assert ind_62.total_wages == 50000.0
    assert ind_62.department_weights["dept_I"] == 0.5
    assert ind_62.occ == 2.0
    assert ind_62.profit_rate == 1.0 / 3.0  # s / (c+v), v=1, c=2 => s/3


def test_industry_xgi_topology():
    import xgi

    ind = IndustryHyperedge(
        naics_2digit="31-33",
        naics_label="Manufacturing",
        department_weights={"dept_I": 0.5},
        member_business_ids={"org_ford", "org_gm"},
        member_worker_block_ids={"class_uaw"},
    )

    H = xgi.Hypergraph()
    members = ind.member_business_ids | ind.member_worker_block_ids
    H.add_edge(members, idx=ind.naics_2digit, label=ind.naics_label)

    assert "org_ford" in H.nodes
    assert "class_uaw" in H.nodes
    assert ind.naics_2digit in H.edges

    edge_members = set(H.edges.members(ind.naics_2digit))
    assert edge_members == members
