# D.A.R.T Capstone Project
D.A.R.T Capstone Project - University of Cincinnati Graduating Class Spring 2027

## The Team
**Sage Reiman** - _Project Management, R&D_ <br/>
**Kaden Jain** - _Scripting, R&D_<br/>
**Kyle Rosa** - _Production, R&D_<br/>
**Jalen Tucker** - _Writing, R&D_<br/>
**Calista Werner** - _Legal, R&D_

## Project Summary
The purpose of this project aims to address the security threats posed by commercial drones entering restricted airspaces and private property. Current kinetic or jamming countermeasures often result in unpredictable drone behavior or collateral damage. This project  develops a non-destructive takeover framework that leverages targeting protocol vulnerabilities in commercial Wi-Fi-based control links.  

The core of the solution is based around a defensive Man-in-the-Middle (MitM) framework designed to intercept the link between a rogue drone and it’s controller. By targeting Wi-Fi channels used to issue control commands to the drone, the system can be used to remotely take control of the drone. This allows for the intentional grounding or recovery of a rouge drone for safety reasons or investigative purposes.  

## Problem Statement
The development of new high-performance commercial drones has outpaced the legal and technical frameworks in place designed to secure infrastructure. According to the FAA’s 2025 Aerospace Forecast, the commercial drone fleet is projected to exceed 1.18 million units by 2029. This growth has led to a documented surge in unauthorized activity Airports or private contractors can face issues with unidentified commercial drones entering their airspace / trespassing onto private property. Vulnerabilities caused by drones can include physical damage caused by the drone and potential network-infrastructure penetration. Existing defense mechanisms such as signal jamming or kinetic weapons can be unpredictable and have the potential to disrupt legitimate communications or cause destruction outside of the intended target.  

## Proposed Solution 
Security gaps in commercial drones make them vulnerable to firmware manipulation, lack of encryption of static data as well as communicated data. By exploiting these security gaps, entities can better defend themselves against drone attacks using a man-in-the-middle takeover to intercept the drone’s connection between it and its controller. A person could remotely takeover the drone through 2.4ghz or 5ghz Wi-Fi channels and then ground it. 

## Project Scope
Due to the complexity of drones and networking systems, there will be many moving parts in the experimentation and research process. It is vital that we keep our scope clear and contained so that our findings and conclusions can be clear with little to no understanding of drones. The primary scope of our solution will be the design and analysis of a man-in-the-middle attack framework on a drone. This is done with the intended purpose of improving the defensive and forensic capabilities of an airport or private contractor, equipping them to defend themselves against drone attacks. This framework will establish controlled communication between the drone and an intermediary device, enabling the safe collection of communication data to better understand and analyze potential vulnerabilities from a defensive and forensic perspective. Additionally, the scope of the solution will include the software used by the controller, the drone, and the exploitation device, as they will need to be examined for the vulnerabilities and use cases. For example, any vulnerabilities found in the drone software will need to be experimented on by the intermediary device to discern which ones will be most useful for defense. Another aspect of the solution which falls under the scope is the impact that this research and experimentation will have on the future of drone forensics, as it could likely be applied in real-world scenarios as drone use becomes more widespread. As for what our scope will not include, there are no plans to investigate any physical drone defenses, as the only devices involved will be those involved in the network connections. Additionally, the specific drone models used will not be explained in too much detail, as the aim of the project is to provide information on the defense structure for drones in general.  

The outline of our solution is as follows: First, we will analyze and evaluate the overall network structure connecting the drone, its controller, and the intermediary device. Second, we will establish the communication link using the appropriate medium, which will most likely be a Wi-Fi channel. The data will be collected and examined from the framework, providing us with useful information to be analyzed. Next, we will use this data to identify the vulnerabilities, experimenting upon them as a part of our primary testing. The exploitation of these vulnerabilities will then be experimented upon to see how they can be used from a defensive perspective. Lastly, the forensic applications of our findings will be investigated and reported on. As a team, we will aim for our primary experimentation and research to be done by January of 2027, leaving the rest of the time to report on our findings and prepare for our writing and presentations.

## Ethical and Legal Considerations
Research into drone vulnerabilities requires a balance between advancing security through intrusion methods while also balancing individual the potential for misuse. As noted by Gabrielsson, Bugeja, and Vogel (2021), the use of open-source software to exploit commercial drones can lead to severe data privacy violations. The risk of threat actors having access to sensitive telemetry, video, and location data presents a significant ethical challenge.  

To mitigate these risks, this project adheres to beneficence and ensuring that the research we do serves primarily the publics’ best interest. This can be accomplished through the equipping of airports and similar public/private sectors with the defensive tools they need regarding rogue drones.  Our project also aims to align with the ACM Code of Ethics, which mandates “avoiding harm” by conducting all testing of MitM interceptions in a controlled, private environment to ensure no third-party data is captured. By defining the scope of this project to defensive recovery and forensic analysis, DART helps provide the ability to secure commercial airspace without compromising the privacy rights of legitimate drone operators.

### References

* Federal Aviation Administration. (2025). FAA Aerospace Forecast Fiscal Years 2025–2045. U.S. Department of Transportation. https://www.faa.gov/data_research/aviation/aerospace_forecasts/2025-faa-aerospace-forecasts.pdf 

* Gabrielsson, J., Bugeja, J., & Vogel, B. (2021). Hacking a commercial drone with open-source software: Exploring data privacy violations. 2021 10th Mediterranean Conference on Embedded Computing (MECO), 1–5. https://doi.org/10.1109/MECO52532.2021.9460295 

* Karmakar, G., Petty, M., Ahmed, H., Das, R., & Kamruzzaman, J. (2022). Security of internet of things devices: Ethical hacking a drone and its mitigation strategies. 2022 IEEE Asia Pacific Conference on Computer Science and Data Engineering (CSDE), 1–5. https://doi.org/10.1109/CSDE56538.2022.10089255 

* White, J. (2021). Drone vulnerabilities. SecQuest. https://www.secquest.co.uk/white-papers/drone-vulnerabilities 
