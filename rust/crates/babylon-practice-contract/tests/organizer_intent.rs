use babylon_practice_contract::{PracticeId, PracticeTargetTag};

#[test]
fn executable_inquiry_and_existing_contact_have_typed_identities() {
    assert!(
        PracticeId::try_from(9).is_ok(),
        "Investigate must be an admitted typed practice"
    );
    assert!(
        PracticeTargetTag::try_from(13).is_ok(),
        "contact must target an existing organization"
    );
}
