import google.generativeai as genai
from load_creds import load_creds
import time

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

genai.configure(credentials=load_creds())

name = "scrape-insight-101"
model = genai.get_tuned_model(f'tunedModels/{name}')

print(model)

operations = genai.list_operations()
operation = list(operations)[1]

"""for status in operation.wait_bar():
  time.sleep(30)"""

plt.figure(figsize=(10, 6))
model = operation.result()

snapshots = pd.DataFrame(model.tuning_task.snapshots)

sns.lineplot(data=snapshots, x = 'epoch', y='mean_loss')
plt.savefig('tuning_loss_plot.png')
plt.show()