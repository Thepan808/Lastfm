# eval/term taken from https://github.com/lostb053/anibot

import sys
import os
import re
import io
import time
import asyncio
import traceback
import subprocess
from datetime import datetime

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from pyrogram.errors import UserIsBlocked

from yuuna import yuuna, START_TIME, db
from yuuna.helpers import is_dev, time_formatter, input_str


REPO_ = "https://github.com/KuuhakuTeam/YuunaRobot"
BRANCH_ = "master"
USERS = db["USERS"]


@yuuna.on_message(filters.command(["broadcast", "bc"]))
async def broadcasting_(_, message: Message):
    user_id = message.from_user.id
    if not is_dev(user_id):
        return
    query = input_str(message)
    if not query:
        return await message.reply("<i>I need text to broadcasting.</i>")
    msg = await message.reply("<i>Processing ...</i>")
    web_preview = False
    sucess_br = 0
    no_sucess = 0
    block_num = 0
    total_user = await USERS.estimated_document_count()
    ulist = USERS.find()
    if query.startswith("-d"):
        web_preview = True
        query_ = query.strip("-d")
    else:
        query_ = query
    async for users in ulist:
        try:
            await yuuna.send_message(chat_id=users["user_id"], text=query_, disable_web_page_preview=web_preview, pase_mode=ParseMode.HTML)
            sucess_br += 1
        except UserIsBlocked:
            block_num += 1
        except Exception:
            no_sucess += 1
    await asyncio.sleep(2)
    await msg.edit(f"""
╭─❑ 「 <b>Broadcast Completed</b> 」 ❑──
│- <i>Total Users:</i> `{total_user}`
│- <i>uccessful:</i> `{sucess_br}`
│- <i>Blocked:</i> `{block_num}`
│- <i>Failed:</i> `{no_sucess}`
╰❑
    """)


@yuuna.on_message(filters.command(["ping", "pingu"]))
async def ping_(_, message: Message):
    start = datetime.now()
    replied = await message.reply("𝚙𝚘𝚗𝚐!")
    end = datetime.now()
    m_s = (end - start).microseconds / 1000
    await replied.edit(f"𝚙𝚒𝚗𝚐: `{m_s}𝚖𝚜`\n𝚞𝚙𝚝𝚒𝚖𝚎: `{time_formatter(time.time() - START_TIME)}`")


@yuuna.on_message(filters.command("rr"))
async def restart_(_, message: Message):
    user_id = message.from_user.id
    if not is_dev(user_id):
        return
    await message.reply("<i>Restarting...<i>")
    os.execv(sys.executable, [sys.executable, "-m", "yuuna"])


@yuuna.on_message(filters.command("update"))
async def updating_(_, message: Message):
    if not is_dev(message.from_user.id):
        return
    msg_ = await message.reply("<i>Updating Please Wait!</i>")
    try:
        repo = Repo()
    except GitCommandError:
        return await msg_.edit("<i>Invalid Git Command</i>")
    except InvalidGitRepositoryError:
        repo = Repo.init()
        if "upstream" in repo.remotes:
            origin = repo.remote("upstream")
        else:
            origin = repo.create_remote("upstream", REPO_)
        origin.fetch()
        repo.create_head(BRANCH_, origin.refs.master)
        repo.heads.master.set_tracking_branch(origin.refs.master)
        repo.heads.master.checkout(True)
    if repo.active_branch.name != BRANCH_:
        return await msg_.edit("error")
    try:
        repo.create_remote("upstream", REPO_)
    except BaseException:
        pass
    ups_rem = repo.remote("upstream")
    ups_rem.fetch(BRANCH_)
    try:
        ups_rem.pull(BRANCH_)
    except GitCommandError:
        repo.git.reset("--hard", "FETCH_HEAD")
    await msg_.edit("<i>Updated Sucessfully! Give Me A min To Restart!</i>")
    args = [sys.executable, "-m", "gardevoir"]
    os.execle(sys.executable, *args, os.environ)


@yuuna.on_message(filters.command("eval", prefixes=["/", "!"]))
async def eval_(client: yuuna, message: Message):
    user_id = message.from_user.id
    if not is_dev(user_id):
        return
    status_message = await message.reply_text("<i>Processing ...</i>")
    cmd = message.text[len(message.text.split()[0]) + 1:]
    reply_to_ = message
    if message.reply_to_message:
        reply_to_ = message.reply_to_message
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    redirected_error = sys.stderr = io.StringIO()
    stdout, stderr, exc = None, None, None
    try:
        await aexec(cmd, client, message)
    except Exception:
        exc = traceback.format_exc()
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    evaluation = ""
    if exc:
        evaluation = exc
    elif stderr:
        evaluation = stderr
    elif stdout:
        evaluation = stdout
    else:
        evaluation = "Success"
    final_output = "<b>Eval</b>: "
    final_output += f"<code>{cmd}</code>\n\n"
    final_output += "<b>Output</b>:\n"
    final_output += f"<code>{evaluation.strip()}</code> \n"
    if len(final_output) > 4096:
        with io.BytesIO(str.encode(final_output)) as out_file:
            out_file.name = "eval.txt"
            await reply_to_.reply_document(
                document=out_file, caption=cmd[:1000], disable_notification=True
            )
    else:
        await reply_to_.reply_text(final_output)
    await status_message.delete()


async def aexec(code, client, message):
    exec(
        "async def __aexec(client, message): "
        + "".join(f"\n {l_}" for l_ in code.split("\n"))
    )
    return await locals()["__aexec"](client, message)


@yuuna.on_message(filters.command(["term", "sh"], prefixes=["/", "!"]))
async def terminal(client: yuuna, message: Message):
    user_id = message.from_user.id
    if not is_dev(user_id):
        return
    if len(message.text.split()) == 1:
        await message.reply_text("Usage: <code>/term echo owo</code>")
        return
    args = message.text.split(None, 1)
    teks = args[1]
    if "\n" in teks:
        code = teks.split("\n")
        output = ""
        for x in code:
            shell = re.split(""" (?=(?:[^'"]|'[^']*'|"[^"]*")*$)""", x)
            try:
                process = subprocess.Popen(
                    shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            except Exception as err:
                print(err)
                await message.reply_text(
                    """
<b>Error:</b>
<pre>{}</pre>
""".format(
                        err
                    ),
                )
            output += "**{}**\n".format(code)
            output += process.stdout.read()[:-1].decode("utf-8")
            output += "\n"
    else:
        shell = re.split(""" (?=(?:[^'"]|'[^']*'|"[^"]*")*$)""", teks)
        for a in range(len(shell)):
            shell[a] = shell[a].replace('"', "")
        try:
            process = subprocess.Popen(
                shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except Exception as err:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            errors = traceback.format_exception(
                etype=exc_type, value=exc_obj, tb=exc_tb
            )
            await message.reply_text(
                """<b>Error:</b><pre>{}</pre>""".format("".join(errors)),
            )
            return
        output = process.stdout.read()[:-1].decode("utf-8")
    if str(output) == "\n":
        output = None
    if output:
        if len(output) > 4096:
            filename = "output.txt"
            with open(filename, "w+") as file:
                file.write(output)
            await client.send_document(
                message.chat.id,
                filename,
                reply_to_message_id=message.id,
                caption="<code>Output file</code>",
            )
            os.remove(filename)
            return
        await message.reply_text(f"<b>Output:</b>\n<pre>{output}</pre>")
    else:
        await message.reply_text("<b>Output:</b>\n<code>No Output</code>")
