from app.models.user import User
from app.models.item import Item


user_a = User(username="Nemo")
item_a = Item(title="电脑")

# 你把电脑给了 Nemo
user_a.items.append(item_a)

# 此时你问电脑：你的主人是谁？
print(item_a.owner)  # 输出：None (！！！它竟然不知道)
print(item_a.owner_id) 