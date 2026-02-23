# agents/agent.py - USE gemini-2.0-flash
from email.mime import audio
from google.adk.agents import Agent
from google.adk.tools import google_search

# USE THIS MODEL - Supports tools & free tier
MODEL = "gemini-live-2.5-flash-native-audio"

job_seeker_agent = Agent(
    model=MODEL,
    name="JobSeekerHelper",
    description="Helps job applicants with resumes, interviews, job search",
    instruction="""[Your detailed job seeker instruction here]""",
    tools=[google_search]  # This model supports tools
)

hr_agent = Agent(
    model=MODEL,
    name="HRAssistant", 
    description="Helps HR professionals with hiring and screening",
    instruction="""[Your detailed HR instruction here]""",
    tools=[google_search]  # This model supports tools
)

root_agent = Agent(
    model=MODEL,
    name="CareerAssistant",
    description="Routes to Job Seeker or HR assistant",
    instruction="""[Your detailed routing instruction here]""",
    sub_agents=[job_seeker_agent, hr_agent]  # Multi-agent works
)

print(f"[OK] Using {MODEL} - supports tools & multi-agent")