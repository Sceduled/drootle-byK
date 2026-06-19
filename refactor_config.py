import ast
from pathlib import Path

# Load file, replace the dictionary.
# It's easier to just overwrite the entire dict using a python script with the text since doing it via replace_file_content might have formatting/indent issues.

new_dict = """SEQUENCE_MESSAGES = {

    # ── SEQUENCE 1: FIRST TOUCH ──────────────────────
    "first_touch": (
        "Hi {name}! I'm Priya from {project_name} "
        "in {area}. You had enquired about our project - "
        "happy to help! Are you looking for a property for self use "
        "or an investment?"
    ),

    # ── SEQUENCE 2: QUALIFICATION NUDGE ──────────────
    "qual_nudge_24h": (
        "Hey {name}, just checking in. "
        "Still exploring options in {area}?"
    ),

    # ── SEQUENCE 3: DNP RECOVERY ──────────────────────
    "dnp_day1": (
        "Hey {name}! Just wanted to check - "
        "did you get a chance to look at the details? "
        "Happy to help if you have any questions"
    ),
    "dnp_day2": (
        "Quick update — {units_sold_this_week} units sold in {project_name} "
        "this week. Thought you'd want to know before deciding."
    ),
    "dnp_day3": (
        "No worries {name}, I understand timing might not "
        "be right. Whenever you're ready, I'm here. "
        "Just drop me a message"
    ),
    "dnp_day5": (
        "Hi {name}, I'll stop following up after this - "
        "just didn't want to close your enquiry "
        "without checking one last time. "
        "Still interested in {area}?"
    ),

    # ── SEQUENCE 4: CALL REMINDERS ────────────────────
    "call_reminder_lead": (
        "Hi {name}!  Just a reminder - "
        "our team will be calling you at {time} today "
        "to discuss {project_name}. "
        "Looking forward to it!"
    ),
    "call_reminder_sales": (
        " SITE VISIT LEAD\\n"
        "{name}\\n"
        "Score: {score}\\n"
        "Size: {industry}\\n"
        "Budget: {budget}\\n"
        "Concern: {pain_point}\\n"
        "Phone: {phone}\\n"
        "Call now to book their site visit."
    ),

    # ── SEQUENCE 5: POST-CALL VALIDATION ─────────────
    "post_call_day1": (
        "Hi {name}. Spoke with you earlier today. "
        "Our team will follow up with the details we discussed "
        "— site visit date, plan, and pricing."
    ),
    "post_call_day2": (
        "Hi {name}! One of our recent buyers was "
        "also looking for {bhk_or_size} in {area}. "
        "They decided to visit {project_name} last week and just booked. "
        "Seeing the space in person really gives clarity."
    ),
    "post_call_day3": (
        "Hi {name}! I've attached a quick walkthrough video "
        "and the floor plans for the {bhk_or_size} options. "
        "Let me know if you have trouble opening them."
    ),
    "post_call_day5": (
        "You mentioned {pain_point} earlier — that's something "
        "our team specifically addresses on every visit, from "
        "loan options to documentation clarity. We want to make sure you have complete confidence."
    ),
    "post_call_day7": (
        "Hi {name}! Just checking - "
        "are you still exploring {project_name}? "
        "We'd love to have you visit this week. "
        "Even a quick 45-min visit gives you "
        "a much clearer picture"
    ),

    # ── SEQUENCE 6: FOMO ──────────────────────────────
    "fomo_day1": (
        "Quick update: {units_sold_this_week} units have moved in {project_name} "
        "this week alone. Wanted to make sure you had this before availability drops further."
    ),
    "fomo_day2": (
        "Hi {name}. Just a heads up — {market_update}. "
        "If you're still considering {area}, this might be the right time to visit."
    ),
    "fomo_day3": (
        "Hi {name}! {current_offer}. "
        "I won't message again after this, but wanted to make sure "
        "you didn't miss out before things change."
    ),

    # ── SEQUENCE 7: LEAD RECOVERY ─────────────────────
    "reactivation_week2": (
        "Hi {name}! Hope you're doing well. "
        "Just wanted to share a quick update: {market_update}. "
        "Thought you might find this useful for your research."
    ),
    "reactivation_week4": (
        "Hi {name}! When choosing a property in {area}, "
        "making sure the RERA documentation and carpet area measurements are clear is critical. "
        "Just a tip to keep in mind while you explore."
    ),
    "reactivation_week6": (
        "Hey {name}! Things change quickly - "
        "are you still keeping an eye out for property "
        "in {area} or have you already found something?"
    ),
    "reactivation_week8": (
        "Hi {name}! We have a few {bhk_or_size} options in {project_name} "
        "that have been very popular for investment lately, rather than just self-use. "
        "Would you be open to exploring a different angle?"
    ),
    "reactivation_week12": (
        "Hi {name}, I'll close your enquiry after this "
        "so I don't keep bothering you. "
        "If anything has changed and you'd like "
        "to explore {project_name} again, I'm just a message away"
    ),

    # ── SEQUENCE 8: CLOSED / REFERRAL + REVIEW ────────
    "closed_day3": (
        "Hi {name}. Welcome to {project_name}. "
        "Our team will be in touch with the next steps "
        "— documentation, payment schedule, and your "
        "dedicated relationship manager."
    ),
    "closed_day14": (
        "Hi {name}. Checking in on how things are going. "
        "Let us know if you need anything."
    ),
    "closed_day30": (
        "Hi {name}! Quick favour - "
        "do you know anyone looking for a home "
        "or investment in {area}? "
        "Would mean a lot if you could refer them. "
        "Happy to take care of them the same way"
    ),
    "closed_day35": (
        "Hi {name}! If you've had a good experience "
        "so far, would you mind sharing a quick "
        "2-line review? "
        "It really helps other families "
        "make the right decision"
    ),

    # ── SEQUENCE 9: UPSELL ────────────────────────────
    "upsell_day1": (
        "Hi {name}! Now that your home is sorted, "
        "have you thought about a commercial unit "
        "or a second property for investment? "
        "Commercial properties in {area} are doing really well"
    ),
    "upsell_day4": (
        "Hi {name}. One of our buyers picked up "
        "an extra property in the same project as an investment "
        "alongside their primary home. "
        "Rental yield in {area} is strong "
        "right now — something to consider."
    ),
    "upsell_day7": (
        "Hi {name}! Want me to have our investment "
        "advisory team give you a quick call? "
        "No pressure - just to see if it makes "
        "sense for your situation"
    ),
}"""

# Actually, the file was already checked out? No, I should revert the client_config.py to pristine then apply the new string.
import subprocess
subprocess.run(['git', 'checkout', 'client_config.py'])

content = Path("client_config.py").read_text("utf-8")
parts = content.split("SEQUENCE_MESSAGES = {")
new_content = parts[0] + new_dict + "\n"
Path("client_config.py").write_text(new_content, "utf-8")
print("Done")
