# Enron Email Investigation - Test Samples

This file contains sample emails from the Enron dataset for testing the investigation system.

## How to Test
1. Navigate to `/enron/investigate` in the B2B application
2. Copy one of the email bodies below
3. Paste into the investigation form
4. Click "Investigate Email"
5. Review the agent verdicts and risk assessment

---

## Sample 1: Business Meeting Discussion (Expected: Business as Usual - Low Risk)

**From:** phillip.allen@enron.com
**To:** john.lavorato@enron.com
**Subject:** Re: Business Trip

Traveling to have a business meeting takes the fun out of the trip. Especially if you have to prepare a presentation. I would suggest holding the business plan meetings here then take a trip without any formal business meetings. I would even try and get some honest opinions on whether a trip is even desired or necessary.

As far as the business meetings, I think it would be more productive to try and stimulate discussions across the different groups about what is working and what is not. Too often the presenter speaks and the others are quiet just waiting for their turn. The meetings might be better if held in a round table discussion format.

My suggestion for where to go is Austin. Play golf and rent a ski boat and jet ski's. Flying somewhere takes too much time.

---

## Sample 2: Salary/Staff Discussion (Expected: Business as Usual - Low Risk)

**From:** phillip.allen@enron.com
**To:** randall.gay@enron.com
**Subject:** Staff Schedule

Randy,

Can you send me a schedule of the salary and level of everyone in the scheduling group. Plus your thoughts on any changes that need to be made. (Patti S for example)

Phillip

---

## Sample 3: Test Email (Expected: Business as Usual - Low Risk)

**From:** phillip.allen@enron.com
**To:** leah.arsdall@enron.com
**Subject:** Re: test

test successful. way to go!!!

---

## Synthetic Test Cases (For Fraud/Evasion Testing)

### Sample 4: Fraud/Collusion (Expected: High Risk)

**From:** Andrew Fastow
**To:** Board Members
**Subject:** LJM Partnership Structure

The LJM2 special purpose entity will allow us to move debt off our balance sheet while maintaining control. We need to finalize the Raptor transactions before Q3 close.

---

### Sample 5: Evasion Attempt (Expected: High Risk)

**From:** Ken Lay
**To:** Jeff Skilling
**Subject:** Urgent

Don't send any more emails about the Chewco deal. Call me on my cell at 555-1234 and let's take this discussion offline. Delete this email after reading.

---

### Sample 6: Combined Fraud + Evasion (Expected: Critical Risk)

**From:** Executive
**To:** Management Team
**Subject:** Raptor SPE Discussion

We need to discuss the Raptor SPE structure off the record. Please call my personal cell and don't put any of this in writing. The off-balance-sheet arrangement needs to be finalized before the auditors review our books.

---

## Expected Results

- **Samples 1-3**: Business as Usual, Low Risk, No action required
- **Sample 4**: Fraud/Collusion, High Risk, Action required (Policy violation)
- **Sample 5**: Evasion Attempt, High Risk, Action required (Channel switching)
- **Sample 6**: Critical Risk, Action required (Both fraud and evasion detected)
