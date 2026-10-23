"""
ecoStock UI test-suite: 5 black-box + 5 white-box Selenium tests.

BLACK-BOX  = behaviour observed only through what a user can see/click.
WHITE-BOX  = tests written with knowledge of the implementation: FEFO comparator,
             the <=3-day markdown window, price arithmetic, ESL sync state machine,
             stock-conservation rules and the reserve-price rule in the store, checked
             against the app's internal state (window.__ECOSTOCK__) and lib/logic.js.
"""
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


# ----------------------------------------------------------------- BLACK BOX
@pytest.mark.blackbox
def test_bb01_landing_and_manager_dashboard_kpis(b):
    """BB-01  Landing page offers 3 portals; Store Manager portal shows the 4 KPIs."""
    b.open("/")
    assert "ecoStock" in b.text("landing-title")
    for role in ("manager", "consumer", "partner"):
        assert b.tid(f"enter-{role}").is_displayed()
    b.click("enter-manager")
    b.tid("kpi-active-batches")
    for kpi in ("active-batches", "items-discounted", "waste-diverted", "revenue-recovery"):
        assert b.tid(f"kpi-{kpi}").is_displayed()
    assert b.text("kpi-active-batches-value") == "12"
    assert b.text("kpi-waste-diverted-value").endswith("kg")
    assert b.text("kpi-revenue-recovery-value").endswith("%")


@pytest.mark.blackbox
def test_bb02_role_switching_shows_tailored_navigation(b):
    """BB-02  Switching role in the navbar swaps the sidebar menu for that persona."""
    b.open("/manager")
    assert {"nav-overview", "nav-inventory", "nav-pricing", "nav-routing"} <= {e.get_attribute("data-testid") for e in b.d.find_elements(By.CSS_SELECTOR, "[data-testid^=nav-]")}
    b.click("role-consumer")
    b.tid("nav-shelf")
    assert b.text("page-title") == "Green Shelf"
    b.click("role-partner")
    b.tid("nav-catalog")
    assert b.text("page-title") == "Bulk Surplus Catalog"
    assert not b.all("nav-pricing")  # manager-only menu must be gone


@pytest.mark.blackbox
def test_bb03_consumer_reserves_item_and_impact_counter_grows(b):
    """BB-03  Shopper reserves a discounted item -> pickup code -> reservation listed -> impact up."""
    b.open("/consumer")
    b.click("nav-impact")
    kg_before = float(b.text("kpi-food-saved-value").split()[0])
    b.click("nav-shelf")
    cards = b.all("shelf-card")
    assert cards, "Green Shelf should list discounted items"
    cards[0].find_element(By.CSS_SELECTOR, "[data-testid=reserve-btn]").click()
    b.tid("reserve-modal")
    b.type("reserve-qty", "2")
    b.pause()
    b.click("reserve-confirm")
    toast = b.text("toast")
    assert "ECO-" in toast
    b.click("nav-reservations")
    assert len(b.all("reservation-table-row")) == 1
    assert b.cells("reservation-table", "status") == ["Reserved"]
    b.click("nav-impact")
    kg_after = float(b.text("kpi-food-saved-value").split()[0])
    assert kg_after > kg_before


@pytest.mark.blackbox
def test_bb04_routing_form_rejects_bad_input(b):
    """BB-04  Secondary-routing form blocks empty, zero, non-numeric and over-stock quantities."""
    b.open("/manager")
    b.click("nav-routing")
    b.click("route-submit")
    assert "Select a batch" in b.text("form-error")
    b.select("route-batch", 1)  # B-1001, 60 units
    b.click("channel-ngo")
    b.select("route-partner", "ngo-1")
    for bad, msg in (("0", "greater than 0"), ("abc", "whole number"), ("999", "Only 60")):
        b.type("route-qty", bad)
        b.click("route-submit")
        assert msg in b.text("form-error"), f"qty={bad!r}"
    assert b.all("dispatch-table-row") == []  # nothing was dispatched


@pytest.mark.blackbox
def test_bb05_ngo_claims_donation_and_confirms_receipt(b):
    """BB-05  NGO accepts a donation dispatch, sees the manifest, confirms receipt."""
    b.open("/partner")
    b.select("persona-select", "ngo-1")
    b.click("filter-donation")
    assert len(b.all("catalog-table-row")) == 2
    b.click("claim-L-9003")
    assert len(b.all("catalog-table-row")) == 1  # claimed lot left the open catalog
    b.click("nav-manifests")
    assert len(b.all("manifest-table-row")) == 1
    b.click("view-MAN-7001")
    assert "City Food Bank" in b.text("manifest-detail")
    b.click("manifest-modal-close")
    b.click("confirm-MAN-7001")
    assert b.cells("manifest-table", "status") == ["Received"]


# ----------------------------------------------------------------- WHITE BOX
@pytest.mark.whitebox
def test_wb01_fefo_order_matches_comparator_and_tiebreak(b):
    """WB-01  Inventory rows follow fefoSort(): expiry ASC, ties broken by batch number."""
    b.open("/manager")
    b.click("nav-inventory")
    expiries = b.cells("inventory-table", "expiry")
    batch_nos = b.cells("inventory-table", "batchNo")
    assert expiries == sorted(expiries), "table must be FEFO ordered"
    in_stock = [x for x in b.state()["batches"] if x["qty"] > 0]
    expected = [x["batchNo"] for x in b.logic("fefoSort", in_stock)]
    assert batch_nos == expected
    # tie-break branch: same expiry -> lexical batch number
    same_day = [(e, n) for e, n in zip(expiries, batch_nos)]
    for (e1, n1), (e2, n2) in zip(same_day, same_day[1:]):
        if e1 == e2:
            assert n1 < n2
    assert b.cells("inventory-table", "rank") == [str(i) for i in range(1, len(batch_nos) + 1)]


@pytest.mark.whitebox
def test_wb02_markdown_window_boundaries(b):
    """WB-02  Pricing panel lists exactly batches with 0 <= daysToExpiry <= 3 (boundary values)."""
    b.open("/manager")
    b.click("nav-pricing")
    shown = set(b.cells("pricing-table", "batchNo"))
    batches = b.state()["batches"]
    days = {x["batchNo"]: b.logic("daysToExpiry", x["expiry"]) for x in batches}
    expected = {n for n, d in days.items() if 0 <= d <= 3}
    assert shown == expected
    assert days["B-1003"] == 0 and "B-1003" in shown          # lower boundary (expires today)
    assert days["B-1004"] == 3 and "B-1004" in shown          # upper boundary (3 days)
    assert days["B-1010"] == 5 and "B-1010" not in shown      # just outside the window
    assert "B-1012" not in shown                              # long shelf life


@pytest.mark.whitebox
def test_wb03_markdown_arithmetic_state_and_esl_sync_machine(b):
    """WB-03  35% on a ₹320 item -> ₹208 in state & DOM; ESL sync goes idle -> syncing -> synced."""
    b.open("/manager")
    b.click("nav-pricing")
    assert b.tid("sync-B-1004").get_attribute("data-state") == "idle"
    assert b.logic("markdownPrice", 320, 35) == 208
    b.click("select-B-1004")
    b.click("tier-35")
    b.click("apply-markdown")
    b.click("confirm-apply")
    assert b.tid("sync-B-1004").get_attribute("data-state") == "syncing"
    WebDriverWait(b.d, 5).until(lambda d: b.tid("sync-B-1004").get_attribute("data-state") == "synced")
    batch = next(x for x in b.state()["batches"] if x["batchNo"] == "B-1004")
    assert (batch["discountPct"], batch["discountedPrice"]) == (35, 208)
    assert b.text("price-B-1004") == "₹208.00"
    # the invalid-tier guard in markdownPrice() really throws
    err = b.d.execute_script("try{window.__ECOSTOCK__.logic.markdownPrice(10,33);return null}catch(e){return e.message}")
    assert "Invalid markdown tier" in err
    # and the markdown propagated to the consumer storefront (shared store)
    b.click("role-consumer")
    assert "B-1004" in [c.get_attribute("data-batch") for c in b.all("shelf-card")]


@pytest.mark.whitebox
def test_wb04_dispatch_conserves_stock_and_feeds_partner_catalog_and_kpi(b):
    """WB-04  Routing 10 units to an NGO: stock -10, history +1, new donation lot, waste KPI +10 kg."""
    b.open("/manager")
    kpi0 = float(b.text("kpi-waste-diverted-value").split()[0])
    s0 = b.state()
    before = next(x for x in s0["batches"] if x["batchNo"] == "B-1001")["qty"]
    lots0 = len(s0["lots"])
    b.click("nav-routing")
    b.select("route-batch", 1)
    b.click("channel-ngo")
    b.select("route-partner", "ngo-2")
    b.type("route-qty", "10")
    b.click("route-submit")
    s1 = b.state()
    after = next(x for x in s1["batches"] if x["batchNo"] == "B-1001")["qty"]
    assert after == before - 10
    assert len(s1["dispatches"]) == 1 and s1["dispatches"][0]["kg"] == 10.0  # 10 units x 1.0 kg
    assert len(s1["lots"]) == lots0 + 1 and s1["lots"][0]["type"] == "donation"
    assert s1["lots"][0]["counted"] is True  # kg already counted -> no double count on receipt
    b.click("nav-overview")
    assert float(b.text("kpi-waste-diverted-value").split()[0]) == round(kpi0 + 10, 1)
    b.click("role-partner")                       # client-side nav keeps the store alive
    b.click("filter-donation")
    assert any("Whole Milk" in t for t in b.cells("catalog-table", "title"))


@pytest.mark.whitebox
def test_wb05_bid_reserve_price_rule_and_winner_allocation(b):
    """WB-05  Bid < reserve is rejected (state untouched); valid bid accepted; winning allocates lot."""
    b.open("/partner")
    b.click("bid-L-9001")                         # reserve = 15000
    b.type("bid-amount", "8000")
    b.click("bid-submit")
    assert "reserve price of ₹15000" in b.text("form-error")
    assert b.state()["bids"] == []                # rejected -> no state mutation
    b.type("bid-amount", "16000")
    b.click("bid-submit")
    s = b.state()
    assert len(s["bids"]) == 1 and s["bids"][0]["amount"] == 16000 and s["bids"][0]["status"] == "Pending"
    b.click("nav-bids")
    b.click("accept-BID-1")
    s = b.state()
    assert s["bids"][0]["status"] == "Won"
    assert next(l for l in s["lots"] if l["id"] == "L-9001")["status"] == "allocated"
    assert len(s["manifests"]) == 1 and s["manifests"][0]["amount"] == 16000
    # an NGO persona must not be able to bid at all (role guard on the button)
    b.click("nav-catalog")
    b.select("persona-select", "ngo-1")
    assert not b.all("bid-L-9002")[0].is_enabled()
