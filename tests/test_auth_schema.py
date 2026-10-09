from app.schemas.auth import CompanyRegisterRequest, CreatorRegisterRequest


def test_company_registration_accepts_legacy_payload_fallbacks():
    values = CompanyRegisterRequest.model_validate(
        {
            "email": "brand@example.com",
            "password": "strong-password",
            "company_name": "Example Brand",
            "company_size": "11-50",
            "website": "https://example.com",
            "description": "A brand description",
            "logo_url": "https://example.com/logo.png",
            "city_state": "Ahmedabad",
            "country": "India",
            "industry": "Retail",
            "marketing_goal": "Increase awareness",
            "creator_categories": ["Business"],
            "platforms": ["Instagram"],
            "purposes": ["Campaigns"],
            "additional_notes": "Contact the marketing team",
        }
    )

    assert values.business_email == "brand@example.com"
    assert values.company_name == "Example Brand"
    assert values.company_website == "https://example.com"
    assert values.company_description == "A brand description"
    assert values.company_logo == "https://example.com/logo.png"
    assert values.creator_categories == ["Business"]
    assert values.additional_notes == "Contact the marketing team"


def test_company_registration_prefers_canonical_payload_fields():
    values = CompanyRegisterRequest.model_validate(
        {
            "businessEmail": "canonical@example.com",
            "email": "fallback@example.com",
            "password": "strong-password",
            "companyName": "Canonical Brand",
            "company_name": "Fallback Brand",
        }
    )

    assert values.business_email == "canonical@example.com"
    assert values.company_name == "Canonical Brand"


def test_creator_registration_accepts_frontend_payload_shape():
    values = CreatorRegisterRequest.model_validate(
        {
            "email": "rs7729808@gmail.com",
            "password": "Lucifer@0911",
            "fullName": "Shah Uday",
            "cityState": "ahmedabad",
            "country": "India",
            "creatorCategory": "Business",
            "contentExperience": "Beginner",
            "contentInterests": ["Startups"],
            "personaGoal": "",
            "profilePic": {"file": {}, "preview": "blob:http://localhost:5173/example"},
            "purposes": ["Track analytics", "Collaborate with brands"],
        }
    )

    assert values.personal_goal == ""
    assert values.profile_pic == {"file": {}, "preview": "blob:http://localhost:5173/example"}


def test_creator_registration_prefers_documented_personal_goal_name():
    values = CreatorRegisterRequest.model_validate(
        {
            "email": "rs7729808@gmail.com",
            "password": "Lucifer@0911",
            "fullName": "Shah Uday",
            "personalGoal": "Grow my audience",
            "personaGoal": "Legacy value",
        }
    )

    assert values.personal_goal == "Grow my audience"
