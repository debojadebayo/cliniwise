# Backend
## Setup Dev Workspace
1. Install [pyenv](https://github.com/pyenv/pyenv#automatic-installer) and then use it to install the Python version in `.python-version`.
    1. install pyenv with `curl https://pyenv.run | bash`
    * This step can be skipped if you're running from the devcontainer image in Github Codespaces
1. [Install docker](https://docs.docker.com/engine/install/)
    * This step can be skipped if you're running from the devcontainer image in Github Codespaces
1. Run `poetry shell`
1. Run `poetry install` to install dependencies for the project
1. Create the `.env` file and source it. The `.env.development` file is a good template.
    1. `cp .env.development .env`
    1. `set -a`
    1. `source .env`
1. Run the database migrations with `make migrate`
1. Run `make run` to start the server locally
    - This spins up the Postgres 15 DB & Localstack in their own docker containers.
    - The server will not run in a container but will instead run directly on your OS.
        - This is to allow for use of debugging tools like `pdb`
1. Lastly, you will likely want to populate your local database with some sample SEC filings
    - We have a script for this! But first, open your `.env` file and replace the placeholder value for the `OPENAI_API_KEY` with your own OpenAI API key
        - At some point you will want to do the same for the other secret keys in here like `AWS_KEY`, & `AWS_SECRET`
    - Source the file again with `set -a` then `source .env`
    - Run `make seed_db_local`
        - If this step fails, you may find it helpful to run `make refresh_db` to wipe your local database and re-start with emptied tables.
    - Done 🏁! You can run `make run` again and you should see some documents loaded at http://localhost:8000/api/document

For any issues in setting up the above or during the rest of your development, you can check for solutions in the following places:
- [`backend/troubleshooting.md`](https://github.com/run-llama/sec-insights/blob/main/backend/troubleshooting.md)
- [Open & already closed Github Issues](https://github.com/run-llama/sec-insights/issues?q=is%3Aissue+is%3Aclosed)
- The [#sec-insights discord channel](https://discord.com/channels/1059199217496772688/1150942525968879636)

## Scripts
The `scripts/` folder contains several scripts that are useful for both operations and development.

## Chat 🦙
The script at `scripts/chat_llama.py` spins up a repl interface to start a chat within your terminal by interacting with the API directly. This is useful for debugging issues without having to interact with a full frontend.

The script takes an optional `--base_url` argument that defaults to `http://localhost:8000` but can be specified to make the script point to the prod or preview servers. The `Makefile` contains `chat` & `chat_prod` commands that specify this arg for you.

Usage is as follows:

```
$ poetry shell  # if you aren't already in your poetry shell
$ make chat
poetry run python -m scripts.chat_llama
(Chat🦙) create
Created conversation with ID 8371bbc8-a7fd-4b1f-889b-d0bc882df2a5
(Chat🦙) detail
{
    "id": "8371bbc8-a7fd-4b1f-889b-d0bc882df2a5",
    "created_at": "2023-06-29T20:50:21.330170",
    "updated_at": "2023-06-29T20:50:21.330170",
    "messages": []
}
(Chat🦙) message Hi


=== Message 0 ===
{'id': '05db08be-bbd5-4908-bd68-664d041806f6', 'created_at': None, 'updated_at': None, 'conversation_id': '8371bbc8-a7fd-4b1f-889b-d0bc882df2a5', 'content': 'Hello! How can I assist you today?', 'role': 'assistant', 'status': 'PENDING', 'sub_processes': [{'id': None, 'created_at': None, 'updated_at': None, 'message_id': '05db08be-bbd5-4908-bd68-664d041806f6', 'content': 'Starting to process user message', 'source': 'constructed_query_engine'}]}


=== Message 1 ===
{'id': '05db08be-bbd5-4908-bd68-664d041806f6', 'created_at': '2023-06-29T20:50:36.659499', 'updated_at': '2023-06-29T20:50:36.659499', 'conversation_id': '8371bbc8-a7fd-4b1f-889b-d0bc882df2a5', 'content': 'Hello! How can I assist you today?', 'role': 'assistant', 'status': 'SUCCESS', 'sub_processes': [{'id': '75ace83c-1ebd-4756-898f-1957a69eeb7e', 'created_at': '2023-06-29T20:50:36.659499', 'updated_at': '2023-06-29T20:50:36.659499', 'message_id': '05db08be-bbd5-4908-bd68-664d041806f6', 'content': 'Starting to process user message', 'source': 'constructed_query_engine'}]}


====== Final Message ======
Hello! How can I assist you today?
```