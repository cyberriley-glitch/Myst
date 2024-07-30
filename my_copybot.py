import discord
from discord.ext import commands
from discord import app_commands
import datetime
import pytz
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import aiohttp


from http_srv import api

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='/', intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

attendance = {}
roles = ['Bartender', 'Manager', 'Courtesan', 'Gambler', 'Security', 'Photographer', 'Receptionist', 'Shouter']

timezone = pytz.timezone('Europe/Berlin')

ATTENDANCE_START_HOUR = 9
ATTENDANCE_END_HOUR = 22

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='/', intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Command tree synced")

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        print(f"Bot is in {len(self.guilds)} guilds")

    async def on_message(self, message):
        if self.user.mentioned_in(message):
            naughty_role = discord.utils.get(message.guild.roles, name="Naughty")
            guest_role = discord.utils.get(message.guild.roles, name="Guest")
            
            if naughty_role in message.author.roles:
                await message.author.remove_roles(naughty_role)
                await message.author.add_roles(guest_role)
                await message.channel.send(f"{message.author.mention}, you've been forgiven! You now have the Guest role.")

        await self.process_commands(message)

bot = Bot()

class AcceptRules(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Accept Rules", style=discord.ButtonStyle.green, custom_id="accept_rules", emoji="✅")
    async def accept_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        guest_role = discord.utils.get(interaction.guild.roles, name="Guest")
        if not guest_role:
            guest_role = await interaction.guild.create_role(name="Guest")

        if guest_role in interaction.user.roles:
            await interaction.response.send_message("You've already accepted the rules!", ephemeral=True)
        else:
            await interaction.user.add_roles(guest_role)
            await interaction.response.send_message("Thank you for accepting the rules. You've been given the Guest role.", ephemeral=True)

    @discord.ui.button(label="I don't accept", style=discord.ButtonStyle.grey, custom_id="dont_accept_rules", emoji="💀")
    async def dont_accept_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        naughty_role = discord.utils.get(interaction.guild.roles, name="Naughty")
        if not naughty_role:
            naughty_role = await interaction.guild.create_role(name="Naughty")

        if naughty_role in interaction.user.roles:
            await interaction.response.send_message("You've already been marked as Naughty!", ephemeral=True)
        else:
            await interaction.user.add_roles(naughty_role)
            await interaction.response.send_message("You've chosen not to accept the rules. You've been given the Naughty role.", ephemeral=True)
            
            # Find or create the #getrolled channel
            getrolled_channel = discord.utils.get(interaction.guild.text_channels, name='getrolled')
            if not getrolled_channel:
                getrolled_channel = await interaction.guild.create_text_channel('getrolled')
            
            # Ping the user with a custom message and GIF
            custom_message = f"Hey {interaction.user.mention}! You've been rolled for not accepting the rules. Enjoy your stay in the naughty corner! 🎭 To get out, just ping the bot."
            
            # Create a file object for the GIF
            gif_file = discord.File("rickrolled.gif", filename="rickrolled.gif")
            
            # Send the message with the GIF
            await getrolled_channel.send(content=custom_message, file=gif_file)

@bot.tree.command(name="setup_rules", description="Set up the rules channel with standard Discord rules")
@app_commands.checks.has_permissions(administrator=True)
async def setup_rules(interaction: discord.Interaction):
    # Check if a 'rules' channel already exists
    rules_channel = discord.utils.get(interaction.guild.text_channels, name='rules')
    
    if not rules_channel:
        # Create a new 'rules' channel if it doesn't exist
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(send_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(send_messages=True)
        }
        rules_channel = await interaction.guild.create_text_channel('rules', overwrites=overwrites)
    
    # Create the embed for rules
    embed = discord.Embed(
        title="Server Rules",
        description="Welcome to our server! Please follow these rules to ensure a positive experience for everyone:",
        color=discord.Color.blue()
    )
    
    rules = [
        "1. Be respectful to all members.",
        "2. No hate speech, racism, or discrimination.",
        "3. No spamming or excessive use of caps.",
        "4. Keep content appropriate and family-friendly.",
        "5. No advertising or self-promotion without permission.",
        "6. Use appropriate channels for discussions.",
        "7. Follow Discord's Terms of Service and Community Guidelines.",
        "8. Listen to and respect the moderators and admins.",
        "9. No sharing of personal information.",
        "10. Have fun and enjoy your time in the server!"
    ]
    
    for rule in rules:
        embed.add_field(name="\u200b", value=rule, inline=False)
    
    embed.set_footer(text="Failure to comply with these rules may result in warnings or bans.")
    
    # Attach the rules.png image
    file = discord.File("rules.png", filename="rules.png")
    embed.set_image(url="attachment://rules.png")
    
    # Send the embed with the attached image and the accept button
    await rules_channel.send(file=file, embed=embed, view=AcceptRules())
    
    await interaction.response.send_message(f"Rules have been set up in {rules_channel.mention}", ephemeral=True)

@setup_rules.error
async def setup_rules_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

#async def bot_main():
#    print("Starting")
#    async with bot:
#        await bot.start(os.environ["BOT_TOKEN"])

class AttendanceView(discord.ui.View):
    def __init__(self, event_date):
        super().__init__(timeout=None)
        self.event_date = event_date

    async def handle_attendance(self, interaction: discord.Interaction, role: str):
        member = interaction.guild.get_member(interaction.user.id)
        display_name = member.nick if member.nick else member.name
        current_time = datetime.datetime.now(timezone)
        
        if self.event_date not in attendance:
            attendance[self.event_date] = {r: {} for r in roles}
        
        if display_name in attendance[self.event_date][role]:
            await interaction.response.send_message(f"{display_name}, you have already been marked present as {role} for {self.event_date}.", ephemeral=True)
        else:
            unix_timestamp = int(current_time.timestamp())
            attendance[self.event_date][role][display_name] = unix_timestamp
            discord_timestamp = f"<t:{unix_timestamp}:T>"
            
            await interaction.response.send_message(f"{display_name} has been marked present as {role} for {self.event_date} at {discord_timestamp}.", ephemeral=True)
            
            await self.update_message(interaction)

    async def remove_attendance(self, interaction: discord.Interaction):
        member = interaction.guild.get_member(interaction.user.id)
        display_name = member.nick if member.nick else member.name

        if self.event_date not in attendance:
            await interaction.response.send_message(f"There are no attendance records for {self.event_date}.", ephemeral=True)
            return

        removed = False
        for role in roles:
            if display_name in attendance[self.event_date][role]:
                del attendance[self.event_date][role][display_name]
                removed = True

        if removed:
            await interaction.response.send_message(f"{display_name}, your attendance has been removed for {self.event_date}.", ephemeral=True)
            await self.update_message(interaction)
        else:
            await interaction.response.send_message(f"{display_name}, you haven't marked your attendance for {self.event_date}.", ephemeral=True)

    async def update_message(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"Attendance for event on {self.event_date}", color=discord.Color.blue())
        
        for role in roles:
            attendees = attendance[self.event_date][role]
            if attendees:
                attendee_list = "\n".join([f"{name} - <t:{time}:t>" for name, time in attendees.items()])
                embed.add_field(name=f"{role} ({len(attendees)})", value=attendee_list, inline=False)
            else:
                embed.add_field(name=f"{role} (0)", value="None", inline=False)
        
        await interaction.message.edit(content=None, embed=embed, view=self)

    @discord.ui.button(label="Bartender", style=discord.ButtonStyle.primary, emoji="🍹")
    async def bartender_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_attendance(interaction, "Bartender")

    @discord.ui.button(label="Manager", style=discord.ButtonStyle.primary, emoji="👔")
    async def manager_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_attendance(interaction, "Manager")

    @discord.ui.button(label="Courtesan", style=discord.ButtonStyle.primary, emoji="💋")
    async def courtesan_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_attendance(interaction, "Courtesan")

    @discord.ui.button(label="Gambler", style=discord.ButtonStyle.primary, emoji="🎲")
    async def gambler_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_attendance(interaction, "Gambler")

    @discord.ui.button(label="Security", style=discord.ButtonStyle.primary, emoji="💪")
    async def security_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_attendance(interaction, "Security")

    @discord.ui.button(label="Photographer", style=discord.ButtonStyle.primary, emoji="📸")
    async def photographer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_attendance(interaction, "Photographer")

    @discord.ui.button(label="Receptionist", style=discord.ButtonStyle.primary, emoji="📋")
    async def receptionist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_attendance(interaction, "Receptionist")

    @discord.ui.button(label="Shouter", style=discord.ButtonStyle.primary, emoji="📢")
    async def shouter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_attendance(interaction, "Shouter")

    @discord.ui.button(label="Remove Attendance", style=discord.ButtonStyle.danger, emoji="❌")
    async def remove_attendance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.remove_attendance(interaction)

async def create_welcome_image(member):
    # Load the custom background image
    background = Image.open("welcome_background.png")
    
    # Resize the background if needed
    background = background.resize((800, 300))  # Adjust size as needed
    
    d = ImageDraw.Draw(background)

    # Load a bold font
    try:
        font = ImageFont.truetype("arialbd.ttf", 40)  # Arial Bold
    except IOError:
        font = ImageFont.truetype("arial.ttf", 40)  # Fallback to regular Arial if bold is not available
        font = ImageFont.truetype(font.path, 40, encoding="unic")  # Make it bold

    # Use display name instead of username
    display_name = member.nick if member.nick else member.name

    # Add text with bright orange color
    text = f"Welcome, {display_name}!"
    bright_orange = (255, 165, 0)  # RGB for bright orange
    
    # Use textbbox to get text dimensions
    bbox = d.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_position = ((800 - text_width) // 2, 220)  # Centered horizontally, 20 pixels from bottom
    d.text(text_position, text, fill=bright_orange, font=font)

    # Get the user's avatar
    async with aiohttp.ClientSession() as session:
        async with session.get(str(member.avatar.url)) as resp:
            if resp.status == 200:
                avatar_data = await resp.read()
                avatar = Image.open(io.BytesIO(avatar_data))
                avatar = avatar.resize((150, 150))
                
                # Create a circular mask
                mask = Image.new('L', (150, 150), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, 150, 150), fill=255)
                
                # Apply the circular mask to the avatar
                output = ImageOps.fit(avatar, mask.size, centering=(0.5, 0.5))
                output.putalpha(mask)
                
                # Paste the circular avatar onto the background image
                avatar_position = ((800 - 150) // 2, 30)  # Centered horizontally, 30 pixels from top
                background.paste(output, avatar_position, output)

    # Save the image to a byte stream
    byte_arr = io.BytesIO()
    background.save(byte_arr, format='PNG')
    byte_arr.seek(0)
    return byte_arr

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="the stars"))

@bot.event
async def on_member_join(member):
    welcome_channel = discord.utils.get(member.guild.channels, name='welcome')
    if welcome_channel:
        embed = discord.Embed(
            title=f"Welcome to the server, {member.display_name}!",
            description="We're glad to have you here. Please read the rules and enjoy your stay!",
            color=discord.Color.orange()
        )
        embed.add_field(name="Member Count", value=f"You are our {len(member.guild.members)}th member!")
        embed.add_field(name="Server Name", value=member.guild.name)
        embed.set_footer(text=f"Joined at {member.joined_at.strftime('%Y-%m-%d %H:%M:%S')}")

        # Create and send the welcome image
        welcome_image = await create_welcome_image(member)
        file = discord.File(fp=welcome_image, filename="welcome.png")
        embed.set_image(url="attachment://welcome.png")

        await welcome_channel.send(file=file, embed=embed)
        
@bot.tree.command(name="start_attendance")
@app_commands.describe(event_date="The date of the event (DD-MM-YYYY)")
@app_commands.checks.has_permissions(administrator=True)
async def start_attendance(interaction: discord.Interaction, event_date: str):
    try:
        date_obj = datetime.datetime.strptime(event_date, "%d-%m-%Y")
        formatted_date = date_obj.strftime("%d-%m-%Y")
    except ValueError:
        await interaction.response.send_message("Invalid date format. Please use DD-MM-YYYY.", ephemeral=True)
        return

    view = AttendanceView(formatted_date)
    embed = discord.Embed(
        title=f"Attendance for event on {formatted_date}",
        description="Click the button corresponding to your role to mark your attendance:",
        color=discord.Color.green()
    )
    for role in roles:
        embed.add_field(name=f"{role} (0)", value="None", inline=False)
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="attendance")
@app_commands.describe(date="The date to show attendance for (DD-MM-YYYY)")
async def show_attendance(interaction: discord.Interaction, date: str = None):
    if date is None:
        date = datetime.datetime.now(timezone).strftime("%d-%m-%Y")
    else:
        try:
            date_obj = datetime.datetime.strptime(date, "%d-%m-%Y")
            date = date_obj.strftime("%d-%m-%Y")
        except ValueError:
            await interaction.response.send_message("Invalid date format. Please use DD-MM-YYYY.", ephemeral=True)
            return
    
    if date in attendance:
        embed = discord.Embed(title=f"Attendance for {date}", color=discord.Color.blue())
        total_attendance = 0
        
        for role in roles:
            if attendance[date][role]:
                attendees = []
                for name, time in attendance[date][role].items():
                    attendees.append(f"{name} - <t:{time}:t>")
                    total_attendance += 1
                
                attendees_str = "\n".join(attendees)
                embed.add_field(name=f"{role} ({len(attendees)})", value=attendees_str, inline=False)
            else:
                embed.add_field(name=f"{role} (0)", value="None", inline=False)
        
        embed.set_footer(text=f"Total Attendance: {total_attendance}")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"No attendance records found for {date}.")

@bot.tree.command(name="daily_report")
@app_commands.describe(date="The date to generate the report for (DD-MM-YYYY)")
@app_commands.checks.has_permissions(administrator=True)
async def daily_report(interaction: discord.Interaction, date: str = None):
    if date is None:
        date = datetime.datetime.now(timezone).strftime("%d-%m-%Y")
    else:
        try:
            date_obj = datetime.datetime.strptime(date, "%d-%m-%Y")
            date = date_obj.strftime("%d-%m-%Y")
        except ValueError:
            await interaction.response.send_message("Invalid date format. Please use DD-MM-YYYY.", ephemeral=True)
            return
    
    if date in attendance:
        embed = discord.Embed(title=f"Daily Attendance Report for {date}", color=discord.Color.green())
        total_attendance = 0
        for role in roles:
            role_count = len(attendance[date][role])
            total_attendance += role_count
            embed.add_field(name=role, value=str(role_count), inline=True)
        embed.set_footer(text=f"Total Attendance: {total_attendance}")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"No attendance records found for {date}.")

