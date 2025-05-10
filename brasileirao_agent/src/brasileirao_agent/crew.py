from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from brasileirao_agent.tools.club_info_tool import ClubInfoTool
from brasileirao_agent.tools.current_round_insight_tool import CurrentRoundInsightsTool
from brasileirao_agent.tools.jogos_tool import JogosTool
from brasileirao_agent.tools.player_overall_tool import PlayerOverallTool
from brasileirao_agent.tools.playerstats_tool import PlayersStatsTool
from brasileirao_agent.tools.round_insights_tool import RoundInsightsTool
from brasileirao_agent.tools.tabela_tool import TabelaTool
from brasileirao_agent.tools.team_overall_tool import TeamOverallTool
from crewai_tools import WebsiteSearchTool

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class BrasileiraoAgent():
    """BrasileiraoAgent crew"""

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def news_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['news_analyst'],
            verbose=True
        )
    
    @agent
    def club_insights_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['club_insights_analyst'],
            verbose=True
        )
    
    @agent
    def tabela_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['tabela_analyst'],
            verbose=True
        )
    
    @agent
    def tabela_performance_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['tabela_performance_analyst'],
            verbose=True
        )
    
    @agent
    def team_stats_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['team_stats_analyst'],
            verbose=True
        )
    
    @agent
    def player_stats_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['player_stats_analyst'],
            verbose=True
        )
    
    @agent
    def player_overall_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['player_overall_analyst'],
            verbose=True
        )
    
    @agent
    def round_insights_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['round_insights_analyst'],
            verbose=True
        )
    
    @agent
    def brasileirao_senior_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['brasileirao_senior_analyst'],
            verbose=True,
            allow_delegation=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def brasileirao_news_task(self) -> Task:
        return Task(
            config=self.tasks_config['brasileirao_news_task'],
            tools=[WebsiteSearchTool()]
        )
    
    @task
    def brasileirao_club_insights_task(self) -> Task:
        return Task(
            config=self.tasks_config['brasileirao_club_insights_task'],
            tools=[ClubInfoTool()]
        )
    
    @task
    def brasileirao_insights_task(self) -> Task:
        return Task(
            config=self.tasks_config['brasileirao_insights_task'],
            tools=[TabelaTool()]
        )
    
    @task
    def brasileirao_team_performance_task(self) -> Task:
        return Task(
            config=self.tasks_config['brasileirao_team_performance_task'],
            tools=[JogosTool()]
        )
    
    @task
    def brasileirao_team_stats_task(self) -> Task:
        return Task(
            config=self.tasks_config['brasileirao_team_stats_task'],
            tools=[TeamOverallTool()]
        )
    
    @task
    def brasileirao_player_stats_task(self) -> Task:
        return Task(
            config=self.tasks_config['brasileirao_player_stats_task'],
            tools=[PlayersStatsTool()]
        )
    
    @task
    def brasileirao_player_overall_task(self) -> Task:
        return Task(
            config=self.tasks_config['brasileirao_player_overall_task'],
            tools=[PlayerOverallTool()]
        )
    
    @task
    def brasileirao_round_insights_task(self) -> Task:
        return Task(
            config=self.tasks_config['brasileirao_round_insights_task'],
            tools=[CurrentRoundInsightsTool(),
                   RoundInsightsTool()]
        )
    
    @task
    def brasileirao_senior_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['brasileirao_senior_analysis_task']
        )

    @crew
    def crew(self) -> Crew:
        """Creates the BrasileiraoAgent crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            manager_llm="gpt-4.1-mini",  # Specify which LLM the manager should use
            llm_manager=self.brasileirao_senior_analyst(), 
            process=Process.hierarchical,  
            planning=True, 
            verbose=True,
            name="Crew_PitacoFC"
        )
