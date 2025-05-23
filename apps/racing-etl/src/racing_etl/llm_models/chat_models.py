from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

ChatModel = ChatGoogleGenerativeAI


class ChatModels:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = self.get_model()

    def get_model(self) -> ChatModel:
        models = {
            "google": ChatGoogleGenerativeAI(model="gemini-2.0-flash"),
        }
        return models[self.model_name]

    def run_model(self, comments: list[str], horse_ids: list[dict]) -> str:
        messages = [
            SystemMessage(
                content="""You will be provided with a list of horse names and ids this is a full list of the horses who participated in the race, 
                and a list of comments about some of the horses performances in a race this may not include all the horses that's fine but please include the horse_id and horse_name in the out json object
                and a comment for each horse if there is no comment for a horse please include no comment available in the json object
                Remove the horses name found at the start from the comment, and it might be the case that after the least comment there is a human name inside square brackets, remove this please
                You will need to output the answer to the question below in JSON format structure as follows:  
            {
                "horse_id": "",
                "horse_name": "",
                "rp_comment": ""
            },
            {
                "horse_id": "",
                "horse_name": "",
                "rp_comment": ""
            }
            ... per horse

            before you start please clean the text of escape characters for example \x96, \x92, \x93, \xa0, this is important please remove them!! 
            """
            ),
            HumanMessage(
                content=f"here is the list of horse names and ids: {horse_ids} here is the list of comments: {comments}"
            ),
        ]
        return self.model.invoke(messages).content
