from agents.base_agent import BaseAgent
agent = BaseAgent('Test_Agent', 'test', 'test')
print('RAW:', repr(agent.ask('Respond ONLY with the JSON: {"test": 123}')))