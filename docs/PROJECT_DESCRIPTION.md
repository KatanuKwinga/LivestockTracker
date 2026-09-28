# Project description (Vilo's brief, transcribed from "Project Description for Claude.docx")

The basis of the project is a web application that enables a farmer to input livestock data and
obtain simple analytics and insights from it to assist with their data-driven decision making.

The data inputs include data for 4 different livestock animals namely: Cattle (Beef/Dairy),
Chicken, Goats and Sheep. The specific data input is divided into categories such as:

- **General information**: date of birth, age, gender, breed, weight and animal descriptions.
- **Commercial data**: where and when the animal was bought, how much it was bought for, how much
  it or its yield was sold for and where it was sold.
- **Health data**: vaccinations received, recent diseases and any treatments given.
- **Breeding data**: number of kids (dead and alive), age of the kids, if expectant, lineage and
  breed quality.
- **Production data**: yield per day (for relevant animals).
- **Mortality data**: date of death, age of death and cause of death.

Output includes charts, percentages, comparisons, means, averages and trend descriptions. In
addition, the outputs of the predictive analytics are shown to the user. These inferences,
predictions and visualisations help the farmer make informed decisions and improve productivity.
The system uses a combination of simple analytics and visualisations of trends, comparisons,
summaries, patterns and warnings, plus "a simple regression model for predictive analysis"
(target originally undetermined; disease/sickness prediction was recommended and chosen).

The system includes authentication and data security. Data is input through forms. Two users:

- **Worker account**: new data input and update of existing data. The worker selects (1) the type
  of livestock (chicken, cows, goats or sheep), then the category of data (general, commercial,
  health, breeding, production or mortality), then either inputs a new animal or updates an
  existing one. The worker can only view the data inputted in table form, search for specific
  data, input new data and update existing records.
- **Farmer account**: views all the analytics, summaries, visualisations, predictions, charts,
  graphs, warnings etc., and uses them to make decisions. The farmer creates the main account and
  creates the worker accounts' credentials. A worker account cannot exist without a farmer
  account first. Accounts are linked to an email; password changes are done through this email.

Analysis diagrams: use case, ERD, sequence diagram, class diagram (summarised in `DESIGN.md`).
Data collection must also be accounted for.

Methodology: OOAD and prototyping. Testing: unit, integration, system and UAT.

## Tools named in the brief (section 3.4)

- Frontend: HTML5, CSS3, **Bootstrap 5**, JavaScript
- Backend: **Flask**, **MySQL**, **SQLAlchemy**
- Environment: Visual Studio Code, GitHub, XAMPP (local dev only; the project instructions
  require the real database to be non-local, hence Aiven)
- Visualisation: **Chart.js** (trends, mean, median, percentages, trend analysis)
- Predictive analytics: **scikit-learn** ("a regression model ... to predict future livestock
  performance"), **Pandas**, **NumPy**

## Project instructions (from the claude.ai project)

Develop step by step, within 6 weeks, a final project with a clean UI/UX, a non-local database, a
functioning backend and a reliable, trained ML model. Include database security with protected
farmer information, authentication, ease of use and reliability, among other non-functional
requirements. Test incrementally, explain what the code does and why so Vilo understands it, and
resolve bugs as they come up.
