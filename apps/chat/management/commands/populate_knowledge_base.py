"""
Management command to populate KnowledgeBase with sample data
Usage: python manage.py populate_knowledge_base
"""
from django.core.management.base import BaseCommand
from apps.chat.models import KnowledgeBase


KNOWLEDGE_BASE_DATA = [
    # Present Simple
    {
        'topic': 'Present Simple - Usage',
        'content': 'The Present Simple tense is used for: 1) habits and routines (I drink coffee every morning), 2) facts and general truths (Water boils at 100°C), 3) scheduled events (The train leaves at 9 AM). Formation: Subject + Base Verb (+ s/es for 3rd person singular).'
    },
    {
        'topic': 'Present Simple - Positive',
        'content': 'Positive form: I/You/We/They + verb. He/She/It + verb + s/es. Examples: I play, You play, He plays, She plays, It plays, We play, They play.'
    },
    {
        'topic': 'Present Simple - Negative',
        'content': 'Negative form: Subject + do/does + not + base verb. I/You/We/They do not (don\'t) play. He/She/It does not (doesn\'t) play. Examples: I don\'t like broccoli, She doesn\'t work here.'
    },
    {
        'topic': 'Present Simple - Questions',
        'content': 'Question form: Do/Does + Subject + base verb? Do I play? Do you play? Does he/she/it play? Do we play? Do they play? Short answers: Yes, I do / No, I don\'t. Yes, he does / No, he doesn\'t.'
    },
    
    # Past Simple
    {
        'topic': 'Past Simple - Usage',
        'content': 'Past Simple is used for: 1) completed actions in the past (I went to Paris last summer), 2) habitual actions in the past (When I was young, I played chess), 3) a sequence of completed actions (I woke up, had breakfast, and went to work).'
    },
    {
        'topic': 'Past Simple - Regular verbs',
        'content': 'Regular verbs: Add -ed to form past tense. Examples: play → played, work → worked, watch → watched, cook → cooked. If verb ends in e, just add -d: live → lived, love → loved.'
    },
    {
        'topic': 'Past Simple - Irregular verbs',
        'content': 'Irregular verbs have special past forms that must be memorized. Common examples: go → went, do → did, have → had, make → made, take → took, come → came, see → saw, say → said, give → gave, find → found, think → thought, know → knew, get → got, write → wrote.'
    },
    {
        'topic': 'Past Simple - Questions and Negatives',
        'content': 'Negatives: Subject + did not (didn\'t) + base verb. I didn\'t go, She didn\'t work. Questions: Did + Subject + base verb? Did you go? Did she work? Short answers: Yes, I did / No, I didn\'t.'
    },
    
    # Present Perfect
    {
        'topic': 'Present Perfect - Usage',
        'content': 'Present Perfect connects past and present. Use for: 1) actions that happened at unknown time (I have seen that movie), 2) actions that started in past and continue (I have lived here for 10 years), 3) recent actions (She has just arrived).'
    },
    {
        'topic': 'Present Perfect - Formation',
        'content': 'Formation: have/has + past participle. I/You/We/They have worked. He/She/It has worked. Regular participles: worked, played, watched. Irregular examples: been, done, seen, gone, eaten, written.'
    },
    {
        'topic': 'Present Perfect - For vs Since',
        'content': 'For: duration (I have worked here for 5 years). Since: starting point (I have worked here since 2020). Use with present perfect to show how long something has been happening. Example: She has studied English since January / She has studied English for 3 months.'
    },
    
    # Vocabulary - Food
    {
        'topic': 'Food - Fruits',
        'content': 'Common fruits: Apple (яблуко), Banana (банан), Orange (апельсин), Lemon (лимон), Strawberry (полуниця), Grape (виноград), Watermelon (кавун), Mango (манго), Pineapple (ананас), Blueberry (чорниця).'
    },
    {
        'topic': 'Food - Vegetables',
        'content': 'Common vegetables: Carrot (морква), Tomato (помідор), Potato (картопля), Lettuce (салат), Onion (цибуля), Garlic (часник), Cucumber (огірок), Pepper (перець), Broccoli (брокколі), Spinach (шпинат).'
    },
    {
        'topic': 'Food - Meat and Fish',
        'content': 'Meat and fish: Chicken (курка), Beef (яловичина), Pork (свинина), Fish (риба), Salmon (лосось), Tuna (тунець), Shrimp (креветка), Crab (краб), Turkey (індик), Lamb (баранина).'
    },
    
    # Daily Activities
    {
        'topic': 'Daily Activities - Morning',
        'content': 'Morning activities: Wake up (прокинутись), Get out of bed (встати з ліжка), Take a shower (прийняти душ), Brush teeth (чистити зуби), Have breakfast (сніданок), Get dressed (одягнутись), Go to work/school (йти на роботу/школу).'
    },
    {
        'topic': 'Daily Activities - Evening',
        'content': 'Evening activities: Come home (приходити додому), Have dinner (вечеря), Watch TV (дивитися телевізор), Read a book (читати книгу), Exercise (робити вправи), Relax (розслабитись), Go to bed (йти спати).'
    },
    
    # Common Phrases
    {
        'topic': 'Common Phrases - Greetings',
        'content': 'Greetings: Hello (привіт), Hi (привіт), Good morning (доброго ранку), Good afternoon (добрий день), Good evening (добрий вечір), How are you? (Як ділиш?) , I\'m fine, thank you (Добре, дякую).'
    },
    {
        'topic': 'Common Phrases - Polite Expressions',
        'content': 'Polite expressions: Please (будь ласка), Thank you (спасибі), You\'re welcome (з задоволенням), Excuse me (вибачте), Sorry (вибачаюсь), I\'m sorry (мені шкода), No problem (не проблема).'
    },
    {
        'topic': 'Common Phrases - Asking for Help',
        'content': 'Help phrases: Can you help me? (Ви можете мені допомогти?), I need help (Мені потрібна допомога), Do you speak English? (Ви говорите англійською?), Could you repeat, please? (Повторіть, будь ласка?), What does it mean? (Що це означає?)'
    },
    
    # Questions
    {
        'topic': 'Questions - Wh-questions',
        'content': 'Wh-questions: What? (Що?), Who? (Хто?), Where? (Де?), When? (Коли?), Why? (Чому?), How? (Як?), Which? (Який?), How much? (Скільки?), How many? (Скільки?). Formation: Wh-word + auxiliary verb + subject + main verb?'
    },
    {
        'topic': 'Questions - Yes/No Questions',
        'content': 'Yes/No questions start with auxiliary verb: Do you play football? (Ти грає в футбол?), Does she like coffee? (Вона любить каву?), Did they go home? (Вони пішли додому?), Have you seen this movie? (Ти бачив цей фільм?)'
    },
    
    # Articles
    {
        'topic': 'Articles - The Indefinite Article A/An',
        'content': 'A/An (неозначений артикль): Use A before consonant sounds (a book, a dog, a university). Use An before vowel sounds (an apple, an egg, an honest man). Use for: first mention (I saw a cat), general statements (A dog is an animal), professions (She is a teacher).'
    },
    {
        'topic': 'Articles - The Definite Article The',
        'content': 'The (означений артикль): Use before: 1) things that are known (The sun, the president), 2) things mentioned before (I saw a cat. The cat was black), 3) unique things (the sea, the sky), 4) with superlatives (the best, the worst), 5) with names of rivers, mountains (the Thames, the Alps).'
    },
    {
        'topic': 'Articles - When NOT to use articles',
        'content': 'No article (0): Before plural nouns (Cats are animals), before uncountable nouns (Water is essential), before general statements (Life is short), with proper nouns (John, London), with possessives (my book, his car), with names of meals (breakfast, dinner), with school/church/bed (go to school, go to bed).'
    },
    
    # Phrasal Verbs
    {
        'topic': 'Phrasal Verbs - Common Examples',
        'content': 'Common phrasal verbs: Wake up (прокинутись), Get up (встати), Put on (одягнути), Take off (зняти), Go out (йти на прогулянку), Come back (повернутись), Look for (шукати), Look after (доглядати), Run into (зустріти випадково), Give up (здатись).'
    },
    {
        'topic': 'Phrasal Verbs - Set 2',
        'content': 'More phrasal verbs: Turn on (увімкнути), Turn off (вимкнути), Turn up (збільшити гучність), Turn down (зменшити гучність), Find out (дізнатись), Work out (розробити, тренуватись), Break down (сломатись), Catch up (наздогнати), Bring back (повернути).'
    },
    
    # Conditional Clauses
    {
        'topic': 'Conditional - First Conditional',
        'content': 'First Conditional (реальна умова): If + Present Simple, + will + base verb. If it rains, I will stay home. If you study hard, you will pass the exam. Used for real, possible situations in the future.'
    },
    {
        'topic': 'Conditional - Second Conditional',
        'content': 'Second Conditional (нереальна умова): If + Past Simple, + would + base verb. If I were rich, I would travel the world. If she studied harder, she would get better marks. Used for imaginary or unlikely situations.'
    },
    {
        'topic': 'Conditional - Zero Conditional',
        'content': 'Zero Conditional (загальна істина): If + Present Simple, + Present Simple. If you heat water to 100°C, it boils. If you mix red and white, you get pink. Used for facts and general truths.'
    },
    
    # Reported Speech
    {
        'topic': 'Reported Speech - Statements',
        'content': 'Reported speech changes tense backward one step: He said "I am happy" → He said he was happy. Direct: "I work here" → Reported: He said he worked there. Direct: "She has finished" → Reported: She said she had finished.'
    },
    {
        'topic': 'Reported Speech - Questions',
        'content': 'Reported questions: Change word order and remove question mark. Direct: "Do you like football?" → Reported: She asked if I liked football. Direct: "Where do you live?" → Reported: He asked where I lived. Use "if/whether" for yes/no questions.'
    },
    
    # Comparatives and Superlatives
    {
        'topic': 'Comparatives - One Syllable',
        'content': 'One syllable adjectives: Add -er for comparative, -est for superlative. Tall → taller → tallest. Big → bigger → biggest. Hot → hotter → hottest. Fast → faster → fastest. Note: Some need doubling (hot, big, sad).'
    },
    {
        'topic': 'Comparatives - Two or More Syllables',
        'content': 'Two+ syllable adjectives: Use "more" for comparative, "most" for superlative. Beautiful → more beautiful → most beautiful. Expensive → more expensive → most expensive. Interesting → more interesting → most interesting. Exception: adjectives ending in -y (happy → happier → happiest).'
    },
    {
        'topic': 'Comparatives - Irregular Forms',
        'content': 'Irregular comparatives: Good → better → best. Bad → worse → worst. Much/Many → more → most. Little → less → least. Far → further/farther → furthest/farthest.'
    },
    
    # Modals
    {
        'topic': 'Modals - Can/Could',
        'content': 'Can/Could: Can - ability (I can swim), permission (You can go), possibility (It can be true). Could - past ability (I could swim when young), possibility (It could be true), permission/politeness (Could I help you?). Cannot (can\'t), Could not (couldn\'t).'
    },
    {
        'topic': 'Modals - Must/Have to',
        'content': 'Must - strong obligation, necessity (You must wear a seatbelt), certainty (She must be sick). Have to - obligation from external source (I have to work). Don\'t have to - no obligation (You don\'t have to come). Mustn\'t - prohibition (You mustn\'t smoke here).'
    },
    {
        'topic': 'Modals - Should/Ought to',
        'content': 'Should/Ought to - advice, recommendations (You should see a doctor), expectations (The bus should arrive soon). Shouldn\'t - not advisable (You shouldn\'t drive tired). Similar meaning, but "should" is more common. Used for giving opinions and suggestions.'
    },
    {
        'topic': 'Modals - May/Might',
        'content': 'May/Might - possibility (It may rain tomorrow), permission (May I sit here?). Might - possibility (She might come). Might is more uncertain than may. Might not - possibility of not happening. Example: He might not come to the party.'
    },
]


class Command(BaseCommand):
    help = 'Populate KnowledgeBase with sample English grammar and vocabulary'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            count = KnowledgeBase.objects.count()
            KnowledgeBase.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {count} existing items'))

        created_count = 0
        for item_data in KNOWLEDGE_BASE_DATA:
            obj, created = KnowledgeBase.objects.get_or_create(
                topic=item_data['topic'],
                defaults={'content': item_data['content']}
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'✓ Successfully created {created_count} knowledge base items')
        )
        self.stdout.write(
            self.style.WARNING(
                '\nNext step: Run: python manage.py generate_embeddings'
            )
        )
