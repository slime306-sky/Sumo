from app.schemas.auth import CreatorRegisterRequest


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
