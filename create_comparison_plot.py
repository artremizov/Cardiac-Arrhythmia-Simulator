import matplotlib.pyplot as plt

# =======================================================
#         CREATE FIGURE 3: CARDIAC OUTPUT COMPARISON
# =======================================================

# --- IMPORTANT ---
# Replace the numbers below with the cardiac output values you
# recorded from running your main simulation for both cases.
co_healthy = 5.88  # The value from your healthy simulation
co_vf = 2.21       # The value from your VF simulation

# --- Plotting Code ---
labels = ['Healthy Baseline', 'Ventricular Fibrillation']
values = [co_healthy, co_vf]

plt.figure(figsize=(7, 6)) # Create a new figure
bars = plt.bar(labels, values, color=['royalblue', 'firebrick'])
plt.ylabel('Cardiac Output (L/min)')
plt.title('Impact of Ventricular Fibrillation on Cardiac Output')
plt.ylim(0, max(values) * 1.25) # Set y-axis limit for better spacing

# Add the numerical values on top of each bar for clarity
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.1, f'{yval:.2f}', ha='center', va='bottom', fontsize=12)

# Save the figure to a file in your project folder
plt.savefig('figure_3_co_comparison.png', dpi=300)

print("Figure 3 has been saved as 'figure_3_co_comparison.png'")

# Display the plot
plt.show()