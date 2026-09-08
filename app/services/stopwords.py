"""Words too common to be interesting as "популярное слово"."""

RU = frozenset(
    """
и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по
только ее её мне было вот от меня еще ещё нет о из ему теперь когда даже ну вдруг
ли если уже или ни быть был него до вас нибудь опять уж вам ведь там потом себя
ничего ей может они тут где есть надо ней для мы тебя их чем была сам чтоб без
будто чего раз тоже себе под будет ж тогда кто этот того потому этого какой совсем
ним здесь этом один почти мой тем чтобы нее неё сейчас были куда зачем всех никогда
можно при наконец два об другой хоть после над больше тот через эти нас про всего
них какая много разве три эту моя впрочем хорошо свою этой перед иногда лучше чуть
том нельзя такой им более всегда конечно всю между это вообще просто очень типа
блин ага ок окей спасибо привет пока ладно короче тоже там вроде именно который
которая которые которых также либо ещё еще ведь всё все этих тех вот какие какого
таки тебе нам вам ими ею ей оно него неё них своей своих свой сами самый наш ваш
наши ваши наша ваша чём чем зато однако причём причем ибо дабы хотя пусть пускай
ну-ка давай давайте ага угу нету есть был была были будут буду будем будешь будете
могу можешь может можем можете могут мог могла могли надо нужно можно нельзя
""".split()
)

EN = frozenset(
    """
the and for you that with this have from are was not but all any can had her his
one our out she they what when who will would there their about after also been
before being between both could did does doing down during each few further here
how into its itself just more most off once only other over own same should some
such than then these those through too under until very were where which while
why with your yours yourself yourselves them then than that these this those too
very can will just don should now got get like yeah yes okay lol omg thanks thank
hello him has hers here its let may might must ours shall upon via
""".split()
)

STOPWORDS = RU | EN
