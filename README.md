# pokemoncards-kimmeh

## MomoYoga Squarespace Integration

Add your MomoYoga class schedule to your Squarespace website.

### Setup

**Prerequisites:** Squarespace Business or Commerce plan (required for Code Blocks).

#### Step 1: Add the stylesheet (optional)

Copy the contents of `momoyoga-squarespace-header.html` and paste it into:
**Page Settings > Advanced > Page Header Code Injection**

This loads MomoYoga's default schedule styling.

#### Step 2: Add the schedule widget

1. In Squarespace, go to **Pages** and open the page where you want the schedule
2. Add a **Code Block** and select **HTML** from the dropdown
3. Copy the contents of `momoyoga-squarespace-embed.html` and paste it in
4. Replace `[schedule URL here]` with your MomoYoga schedule URL (e.g., `https://www.momoyoga.com/yourstudioname`)
5. Save and publish

### How it works

- Displays your upcoming classes for the next 8 weeks (max 100 classes)
- Visitors can click "Book now" to be redirected to MomoYoga for registration
- Uses MomoYoga's official schedule plugin (v2)

### Resources

- [MomoYoga Squarespace Guide](https://support.momoyoga.com/en/support/solutions/articles/201000109944)
- [MomoYoga JavaScript Integration](https://support.momoyoga.com/en/support/solutions/articles/201000111696)
- [MomoYoga Integration Options](https://help.momoyoga.com/hc/en-us/articles/115003487851)