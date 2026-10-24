use super::artifact;
use super::artifact::{WorldReferenceError, POPULATION, TRADE};
use super::parse;

fn population_rows() -> Vec<Vec<String>> {
    artifact::decode(POPULATION)
        .expect("the committed canonical bytes decode")
        .lines()
        .skip(1)
        .map(|line| {
            crate::reference_csv::record(line, 14)
                .expect("the fixture call `record` succeeds for the authored inputs")
        })
        .collect()
}

#[test]
fn absent_or_parent_counted_population_cannot_become_an_additive_zero() {
    for identity in ["m49:581", "m49:162", "census:5082"] {
        let mut row = population_rows()
            .into_iter()
            .find(|row| row[0] == identity)
            .expect("the fixture holds the searched element");
        assert!(parse::population_row(&row).is_ok());
        row[5] = "0".to_owned();
        assert_eq!(
            parse::population_row(&row),
            Err(WorldReferenceError::Population)
        );
    }
}

#[test]
fn source_projection_cannot_claim_observation_or_hide_its_date_and_row() {
    let row = population_rows()
        .into_iter()
        .find(|row| row[0] == "m49:124")
        .expect("the fixture holds the searched element");
    for (column, value) in [
        (6, "Observed"),
        (7, "census"),
        (8, "2025-07-01"),
        (10, "0"),
        (13, "NaN"),
    ] {
        let mut changed = row.clone();
        changed[column] = value.to_owned();
        assert_eq!(
            parse::population_row(&changed),
            Err(WorldReferenceError::Population)
        );
    }
}

#[test]
fn dependency_and_foreign_population_parents_cannot_cross_scopes() {
    let mut members = artifact::world_reference()
        .expect("the world reference fixture loads")
        .members()
        .to_vec();
    let child = members
        .iter_mut()
        .find(|row| row.identity() == "m49:162")
        .expect("the fixture holds the searched element");
    child.population.accounted_in = Some("m49:124".to_owned());
    assert_eq!(
        parse::finish(members),
        Err(WorldReferenceError::ParentRelation)
    );
}

#[test]
fn annual_trade_availability_cannot_be_replaced_with_a_money_like_default() {
    let trade = artifact::decode(TRADE).expect("the committed canonical bytes decode");
    let mut missing = trade
        .lines()
        .skip(1)
        .map(|line| {
            crate::reference_csv::record(line, 47)
                .expect("the fixture call `record` succeeds for the authored inputs")
        })
        .find(|row| row[0] == "m49:581")
        .expect("the fixture holds the searched element");
    assert!(parse::trade_row(&missing).is_ok());
    missing[15] = "0".to_owned();
    assert_eq!(parse::trade_row(&missing), Err(WorldReferenceError::Trade));
}

#[test]
fn source_record_quoting_is_strict_and_unicode_names_are_preserved() {
    assert_eq!(
        crate::reference_csv::record("\"Åland, islands\",\"a\"\"b\",", 3)
            .expect("the fixture call `record` succeeds for the authored inputs"),
        ["Åland, islands", "a\"b", ""]
    );
    for row in ["\"unterminated,a", "a\"b,c", "\"a\"tail,b", "a,b,c", "a,\t"] {
        assert!(crate::reference_csv::record(row, 2).is_err(), "{row}");
    }
}
