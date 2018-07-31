import db,action,logger,errors,utils,helpMessages
import argparse,discord,datetime

class CommandManager:
    """Handles command detection and emoji reaction detection"""
    def __init__(self,client,logger,db,sw):
        self.client = client
        self.logger = logger
        self.db = db
        self.serverWrapper = sw
        # TODO: Add admin commands for adjusting quorum, thresholds, and delay
        # _DDD {command} {params}
        # command = add
        #   params[0] = kick
        #       _DDD add kick {target}
        #   params[0] =  ban
        #       _DDD add ban {target} {duration}
        # command = about
        #   _DDD about
        # command = status
        #   _DDD status {propIndex}
        # command = help
        #   _DDD help [command]
        # command = admin
        #   _DDD admin -d [PropDelay] -q [Quorum %]

        # Setup commands
        #NOTE: the add command is so large and diverse, it has it's own ArgumentParser that is passed the result from the
        # add command.
        topParser = argparse.ArgumentParser(prog="_DDD")
        addParser = argparse.ArgumentParser(prog="add")

        # Fill out top level parser
        topSubparsers = topParser.add_subparsers(dest="command")

        topSubparser_add = topSubparsers.add_parser("add")
        topSubparser_add.add_argument("parameters",type=str,nargs='+')

        topSubparser_status = topSubparsers.add_parser("status")
        topSubparser_status.add_argument("propIndex",type=int,nargs=1,help="The internal index of the prop to create a status message for.")

        topSubparser_help = topSubparsers.add_parser("help")
        topSubparser_help.add_argument("-c","--helpCommand",required=False,type=str)

        topSubparser_admin = topSubparsers.add_parser("admin")
        topSubparser_admin.add_argument("-d","--delay",required=False,type=str,help="The specific delay for the server")
        topSubparser_admin.add_argument("-q","--quorum",required=False,type=int,help="The specific quorum for the server")

        topSubparser_about = topSubparsers.add_parser("about")
        # Fill out add parser
        addSubparsers = addParser.add_subparsers(dest="type")

        addSubparsers_kick = addSubparsers.add_parser("kick")
        addSubparsers_kick.add_argument("target",type=str,nargs=1)

        addSubparsers_ban = addSubparsers.add_parser("ban")
        addSubparsers_ban.add_argument("target",type=str,nargs=1)
        addSubparsers_ban.add_argument("duration",type=str,nargs=1)

        # Finalize
        self.topParser = topParser
        self.addParser = addParser
        self.topSubparser_admin = topSubparser_admin
        self.topSubparser_help = topSubparser_help
        self.topSubparser_status = topSubparser_status
        self.topSubparser_about = topSubparser_about
    async def handleMessage(self,message):
        """Routes and executes command methods"""
        if message.content[:4] != '_DDD':
            return
        try:
            parsedCommand = self.topParser.parse_args(message.content[4:].split())
        except: # User error
            #TODO: Implement error handling
            #NOTE: Better error messages (e.g the help messages from the argparse library) aren't possible
            # due to the design of the argparse library not returning those messages in the exception :(
            await self.logger.error("There was an error in your command.  If you would like a help message,  use the command _DDD help.", message.channel)
            return
        route = {
            "add": self.add,
            "status": self.status,
            "help": self.help,
            "admin": self.admin,
            "about": self.about
        }
        await route[parsedCommand.command](parsedCommand,message)

    async def handleEmoji(self,reaction,user):
        """Handles an emoji reaction to a message"""
        e = str(reaction.emoji)
        if e.startswith(('👍','👎')):
            action = await self.db.query_one({'messageId':reaction.message.id,'active':True})
            if e.startswith('👍'):
                await self.handleVote(user,'y',action,reaction.message)
            else:
                await self.handleVote(user,'n',action,reaction.message)
        elif e.startswith('❌'):
            action = await self.db.query_one({'messageId':reaction.message.id,'active':True})
            await self.handleRemoveStatus(user,action,reaction.message)
    async def handleRemoveEmoji(self,reaction,user):
        """Handles an emoji being removed from a message"""
        e = str(reaction.emoji)
        if e.startswith(('👍','👎')):
            action = await self.db.query_one({'messageId':reaction.message.id,'active':True})
            if e.startswith('👍'):
                await self.handleRemoveVote(user,'y',action,reaction.message)
            else:
                await self.handleRemoveVote(user,'n',action,reaction.message)

    async def add(self,parsed,message):
        """The add command adds a proposition, and it's response is the status message"""
        # Pull the params out
        try:
            parsedAdd = self.addParser.parse_args(parsed.parameters)
        except: #TODO: Implement error handling
            await self.logger.error("There was an error with the add command's parameters.  Check '_DDD help -c add' for help.", message.channel)
            return
        # Add the prop to the DB
        # I wish there was a way that wasn't if/else chains...
        propType = parsedAdd.type
        propAction = None
        if propType == "kick":
            propAction = action.DDDAction.KickAction(message,message.author,parsedAdd.target[0])
        elif propType == "ban":
            propAction = action.DDDAction.BanAction(message,message.author,parsedAdd.target[0],utils.toSeconds(parsedAdd.duration[0]))
        else:
            #TODO: Implement error handling
            await self.logger.error("There was an error with the prop type %s.  Check '_DDD help -c add' for a list of prop types" % propType, message.channel)
            return
        # Print status message for prop 
        # NOTE: As the status message id is added to the prop, this must be done before storing the prop
        # If you do not, it default's to the command message
        propAction.messageId = await self.logger.status(propAction,message.channel)
        # Store prop
        await self.db.store_action(propAction)
        # Done!  
    async def status(self,parsed,message):
        """The status command creates a new link message that you can add emoji\n reactions to"""
        pass
    
    async def about(self,parsed,message):
        """The about command prints simple information about the bot"""
        #TODO: Fill in TBD
        about_info = "**Author**\n"\
                    "Jonas#1723\n\n"\
                    "**Guilds**\n"\
                    "TBD\n"\
                    "**Open Propositions**\n"\
                    "TBD\n"\
                    "**Total Propositions**\n"\
                    "TBD\n"
        embed = discord.Embed(type="rich",color=discord.Color.blue(),description=about_info,title="Direct Discord Democracy")
        await self.client.send_message(message.channel,embed=embed)
    
    async def help(self,parsed,message):
        """The help command prints out help info on commands"""
        helpMessage = None
        if not parsed.helpCommand:
            # General help
            helpMessage = "%s\n%s" % (self.topParser.format_help(),helpMessages.generalHelp)
        elif parsed.helpCommand == "add":
            helpMessage = "%s\n%s" % (self.addParser.format_help(),helpMessages.genAddHelp(message.server))
        #NOTE: the remove command has been removed (hahaha)
        elif parsed.helpCommand == "status":
            helpMessage = "%s\n%s" % (self.topSubparser_status.format_help(),helpMessages.statusHelp)
        elif parsed.helpCommand == "admin":
            helpMessage = "%s\n%s" % (self.topSubparser_admin.format_help(),helpMessages.adminHelp)
        elif parsed.helpCommand == "about":
            helpMessage = "%s\n%s" % (self.topSubparser_about.format_help(),helpMessages.aboutHelp)
        else:
            # TODO: Error handling
            await self.logger.log("Help for command %s not found" % parsed.helpCommand, message.channel)
            return
        await self.logger.log(helpMessage,message.channel)

    async def admin(self,parsed,message):
        """An admin command to set server-wide values"""
        # Check to see if the user is an admin
        if not message.author.server_permissions.administrator:
            await self.logger.error("You have insufficient permissions to execute this command",message.channel)
            return

        quorum = parsed.quorum
        delay = parsed.delay

        # Pre processing
        if delay:
            delay = utils.toSeconds(delay)
        if quorum:
            quorum = int(quorum)/100

        # Check if the quorum is in range
        if quorum and (quorum > 1 or quorum < 0.01):
            #TODO: Error handling
            await self.logger.error("There was an error with the admin command's quorum parameter.  Check '_DDD help -c admin' for help.", message.channel)
        
        # Execute the update and wait for status
        status = await self.serverWrapper.updateServerData(message.server,quorum,delay)
        if status:
            await self.logger.success("Successfully changed server values",message.channel)
        else:
            pass #TODO: Add error handling

    async def handleVote(self,user,vote,action,message):
        """Handle function that should only be called by handleEmoji"""
        # TODO: If any time the vote action fails, remove the vote.
        
        doc = await self.db.query_one({'messageId':action.messageId})
        # Check to make sure the props are active
        if not doc.active:
            # TODO: Remove the reaction
            return

        # Verify one-time vote
        voters = doc.voters
        if user.id in voters:
            # Silent error because not caused by user
            # TODO: Remove the second vote/reaction
            return

        # Update vote count in DB
        if vote == 'y':
            action.y = action.y + 1 #NOTE: I don't requery the DB to save time
            await self.db.update_one(action,{'$inc':{'y':1}})
        elif vote == 'n':
            action.n = action.n + 1 #NOTE: I don't requery the DB to save time
            await self.db.update_one(action,{'$inc':{'n':1}})
        await self.db.update_one(action,{'$addToSet':{'voters':user.id}}) #TODO: Batch updates?

        # Update vote count in message
        log_message = action.formatAction()
        embed = discord.Embed(type="rich",color=self.logger.colors['status'],description=log_message)
        await self.client.edit_message(message,embed=embed)

    async def handleRemoveVote(self,user,vote,action,message):
        """Handle function that should only be called by handleRemoveEmoji"""
        # Update vote count in DB
        if vote == 'y' and action.y > 0:
            action.y = action.y - 1 #NOTE: I don't requery the DB to save time
            await self.db.update_one(action,{'$inc':{'y':-1}})
        elif vote == 'n' and action.n > 0:
            action.n = action.n - 1 #NOTE: I don't requery the DB to save time
            await self.db.update_one(action,{'$inc':{'n':-1}})
        else:
            # TODO: Error handling
            return

        #NOTE: If user is None, we don't know who to mark off a vote for.  We have to just subtract the vote from the tally
        # and live with it.  This is a big issue.
        if user:
            await self.db.update_one(action,{'$pull':{'voters':user.id}}) #TODO: Batch updates?

        # Update vote count in message
        log_message = action.formatAction()
        embed = discord.Embed(type="rich",color=self.logger.colors['status'],description=log_message)
        await self.client.edit_message(message,embed=embed)

    async def handleRemoveStatus(self,user,action,message):
        """Handle function that should only be called by handleEmoji"""
        if user.id != action.created_by:
            #TODO: Remove their reaction
            return
        
        # Deactivate action
        action.active = False
        await self.db.update_one(action,{'$set':{'active':False}})

        # Update status message
        log_message = action.formatAction()
        embed = discord.Embed(type="rich",color=self.logger.colors['inactive'],description=log_message)
        await self.client.edit_message(message,embed=embed)