import json
from trello import TrelloClient
from amp.task.manager import TaskManager
import logging
from collections import namedtuple

class TaskTrello (TaskManager):
     """Subclass of TaskManager implementing HMGM task management with Trello platforms."""


     # Set up trello instance with properties in the given configuration instance.
     def __init__(self, config):
         super().__init__(config)

         # get trello server info from the config 
         trello_api_key = config["trello"]["api_key"]
         trello_api_token = config["trello"]["api_token"]
         trello_board_id = config["trello"]["board_id"]    
         self.trello = TrelloClient(api_key=trello_api_key, token=trello_api_token)
         self.board = self.trello.get_board(trello_board_id)
         self.todo_list = self.get_list_by_name('to do')
         self.done_list = self.get_list_by_name('done')



     # Create a trello card given the task_type, context, input/output json, 
     # save information about the created card into a JSON file, and return the card.
     def create_task(self, task_type, context, editor_input, task_json):
         labels = self.get_labels([task_type])
        #  check labels in list of labels and get match ids
         summary = context["primaryfileName"] + " - " + context["workflowName"]
         description = self.get_task_description(task_type, context, editor_input)
         card = self.todo_list.add_card(name=summary, desc=description, labels=labels)
         # extract important information (ID, key, and URL) of the created issue into a dictionary, which is essentially the response returned by Trello server
         issue_dict = {"id": card.id, "key": card.short_id, "url": card.short_url }
         # write trello card into task_json file to indicate successful creation of the task
         with open(task_json, "w") as task_file:
             json.dump(issue_dict, task_file)

         return namedtuple('Struct', issue_dict.keys())(*issue_dict.values())
     
     # Close the trello card specified in task_json by updating its status and relevant fields, and return the issue.          
     def close_task(self, task_json):
         # read trello card info from task_json into a dictionary
         with open(task_json, 'r') as task_file:
             issue_dict = json.load(task_file)

         # get the trello issue using id
         card = self.trello.get_card(issue_dict["id"])
         try:
            card.change_list(self.done_list.id)
            logging.info("Transition issue " + card.id + " to status DONE")
         except Exception as e:
             logging.warning("Issue  " + card.id + " is already Done, probably closed manually by someone")
         return namedtuple('Struct', issue_dict.keys())(*issue_dict.values())


     def get_list_by_name(self, name):
         lists = self.board.list_lists()
         for list in lists:
             if list.name.lower() == name:
                 return list
             
     def get_labels(self, input):
         labels = self.board.get_labels(fields='all', limit=100)
         output = []
         for label in labels:
             if label.name in input:
                 output.append(label)
         return output
