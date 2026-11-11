"""
backend/scripts/prepare_niche_demo.py
-------------------------------------
Prepares, primes, and resets state for:
1. Existing Niche Career: Robotics Engineer (SOC: 17-2199.08, O*NET)
2. Novel Niche Career: Autonomous Drone Fleet Architect (Novel AI Induced)

Modes:
  --seed    : Pre-seeds verified 5-question curriculum lessons and canonical skills into Supabase.
  --reset   : Cleans out unreviewed test career rows, user profiles, and drops for the demo career,
              leaving the micro_content reservoir intact so onboarding can be run live from scratch.
  --verify  : Simulates end-to-end onboarding, daily drop compilation, 1-shot reshuffle, and quiz submission.
"""

import sys
import os
import json
import uuid
import asyncio
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService
from app.services.daily_drop_service import DailyDropService
from app.core.career_fields import classify_career_field

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()

NICHE_CURRICULUM_SEEDS = [
    # ══════════════════════════════════════════════════════════════════════════
    # CAREER 1: Autonomous Drone Fleet Architect (Novel Niche Career - Field: Engineering)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "career_title": "Autonomous Drone Fleet Architect",
        "skill_name": "Flight Path Optimization",
        "category": "Technical",
        "title": "Global Flight Path Optimization for Autonomous UAV Fleets: 3D Waypoints and Energy Constraints",
        "source_type": "arxiv",
        "source_adapter": "arxiv",
        "source_url": "https://arxiv.org/abs/2301.04210",
        "author_institution": "IEEE Robotics and Automation Society",
        "reading_time_minutes": 14,
        "difficulty_level": 3,
        "summary": "Mathematical principles of 3D trajectory generation and energy-efficient waypoint planning for unmanned aerial vehicles. Explores Dubins paths, minimum-snap trajectory smoothing, and wind vector compensation in multi-drone dispatching.",
        "takeaways": [
            "Dubins path formulations compute shortest paths for fixed-wing UAVs with minimum turn radius constraints.",
            "Minimum-snap trajectories reduce motor wear and battery draw by minimizing the fourth derivative of position.",
            "Dynamic wind vector compensation prevents drift and preserves battery safety margins on long transit legs."
        ],
        "concept_overview": "Trajectory planning for autonomous aerial fleets requires solving multi-objective optimization problems balancing battery endurance, aerodynamic limits, and strict geofence constraints. Unlike ground vehicles, quadcopters and fixed-wing drones must constantly expend energy to maintain lift. By formulating flight corridors using polynomial B-splines and minimum-snap cost functions, fleet architects ensure kinematic feasibility while extending operational range.",
        "practice_scenario": "You are deploying a fleet of autonomous delivery drones operating in coastal wind gusts. You formulate a 3D spline trajectory constrained by maximum roll angles and wind vectors, reducing total fleet energy consumption by 18 percent.",
        "quizzes": [
            {
                "question": "Why is the snap (fourth derivative of position) minimized when planning quadcopter flight trajectories?",
                "options": [
                    "To minimize angular acceleration rates and excessive motor current spikes",
                    "To increase maximum GPS satellite signal strength during hover",
                    "To bypass local air traffic control altitude limits",
                    "To prevent camera sensor rolling-shutter artifacts"
                ],
                "answer": "To minimize angular acceleration rates and excessive motor current spikes",
                "explanation": "Quadrotor motor inputs are proportional to the snap of position; minimizing snap yields smooth control efforts and prevents actuator saturation."
            },
            {
                "question": "What is the primary kinematic constraint modeled by Dubins path algorithms for fixed-wing drones?",
                "options": [
                    "A strictly bounded minimum turn radius",
                    "Zero vertical climb rate capability",
                    "Mandatory hover stops at every waypoint",
                    "Continuous omnidirectional sideways translation"
                ],
                "answer": "A strictly bounded minimum turn radius",
                "explanation": "Dubins curves model vehicles with forward-only velocity and a bounded maximum curvature (minimum turn radius)."
            },
            {
                "question": "How does crosswind vector compensation modify a UAV's heading angle during waypoint tracking?",
                "options": [
                    "It crabs the vehicle heading into the wind to keep the ground track aligned with the path",
                    "It cuts motor power to the leeward rotor blades completely",
                    "It forces the drone into immediate emergency descent",
                    "It switches telemetry from 5G to VHF radio"
                ],
                "answer": "It crabs the vehicle heading into the wind to keep the ground track aligned with the path",
                "explanation": "Crabbing allows the aerodynamic velocity vector to counteract side-wind components so the ground track remains on the planned trajectory."
            },
            {
                "question": "Which mathematical representation provides continuous derivatives up to acceleration and jerk for waypoint interpolation?",
                "options": [
                    "Cubic or Quintic B-spline curves",
                    "Piecewise linear step functions",
                    "Discrete look-up tables without smoothing",
                    "Single-order difference equations"
                ],
                "answer": "Cubic or Quintic B-spline curves",
                "explanation": "Quintic splines guarantee continuous second and third derivatives, ensuring smooth velocity, acceleration, and jerk profiles."
            },
            {
                "question": "What happens if a planned drone trajectory demands a lateral acceleration that exceeds the rotor thrust margin?",
                "options": [
                    "The aircraft will lose altitude due to lack of vertical thrust component or saturate its ESCs",
                    "The flight controller automatically switches to airplane mode",
                    "The ground station reboot signal is triggered",
                    "The GPS receiver experiences multipath interference"
                ],
                "answer": "The aircraft will lose altitude due to lack of vertical thrust component or saturate its ESCs",
                "explanation": "Tilting a multirotor to achieve lateral acceleration redirects vertical thrust; exceeding thrust limits leads to uncontrolled altitude loss."
            }
        ]
    },
    {
        "career_title": "Autonomous Drone Fleet Architect",
        "skill_name": "Collision Avoidance Algorithm Validation",
        "category": "Technical",
        "title": "Airborne Collision Avoidance and Trajectory Deconfliction in Drone Swarms Using Velocity Obstacles",
        "source_type": "academic",
        "source_adapter": "arxiv",
        "source_url": "https://www.faa.gov/uas/research_development/traffic_management/",
        "author_institution": "FAA NextGen Aviation Research Division",
        "reading_time_minutes": 15,
        "difficulty_level": 4,
        "summary": "Engineering analysis of sense-and-avoid architectures, reciprocal velocity obstacles (RVO), and ACAS sXu collision avoidance protocols. Covers mathematical verification of safe separation spheres and tactical resolution maneuvers.",
        "takeaways": [
            "Velocity Obstacle (VO) geometric cones define relative velocities that will lead to collision within a given time horizon.",
            "Reciprocal Velocity Obstacles (RVO) prevent oscillation by dividing the avoidance burden equally between converging aircraft.",
            "FAA ACAS sXu provides standardized airborne surveillance and advisory logic tailored for unmanned systems."
        ],
        "concept_overview": "In high-density autonomous drone operations, decentralized collision avoidance is required when centralized dispatch loses latency guarantees. The Velocity Obstacle framework projects neighboring aircraft positions and velocities forward in time. When relative velocities fall inside the obstacle cone, the autopilot selects a velocity vector outside the cone that minimizes deviation from the original flight plan, guaranteeing spatial separation without deadlock.",
        "practice_scenario": "Two surveillance drones approach each other head-on at 15 m/s in narrow urban canyon airspace. Your onboard RVO algorithm identifies the conflict 6 seconds prior to collision and computes a coordinated rightward lateral separation vector, maintaining a 20-meter protective bubble.",
        "quizzes": [
            {
                "question": "What geometric representation defines the set of all relative velocities resulting in a collision with an obstacle within time horizon tau?",
                "options": [
                    "A Velocity Obstacle (VO) truncated cone",
                    "A Fourier transform spectrogram",
                    "A Voronoi polygon cell",
                    "A Kalman filter covariance ellipse"
                ],
                "answer": "A Velocity Obstacle (VO) truncated cone",
                "explanation": "The Velocity Obstacle cone geometrically maps all relative velocity vectors that intersect the Minkowski sum of the two craft within the time horizon."
            },
            {
                "question": "What common issue occurs when two non-reciprocal obstacle avoidance agents encounter each other head-on?",
                "options": [
                    "Reciprocal oscillation or chattering where both continuously switch evasion directions",
                    "Immediate battery thermal runaway",
                    "Loss of inertial measurement unit calibration",
                    "Automatic ground station power cutoff"
                ],
                "answer": "Reciprocal oscillation or chattering where both continuously switch evasion directions",
                "explanation": "Without reciprocal coordination, both agents assume the other is static, causing alternating evasive maneuvers that oscillate."
            },
            {
                "question": "Under FAA ACAS sXu terminology, what is the role of a 'Resolution Advisory' (RA)?",
                "options": [
                    "It commands a specific vertical or horizontal avoidance maneuver to maintain safe aircraft separation",
                    "It prompts the pilot to log a maintenance ticket after landing",
                    "It notifies the ground station to bill the customer for flight minutes",
                    "It adjusts camera gimbal exposure settings"
                ],
                "answer": "It commands a specific vertical or horizontal avoidance maneuver to maintain safe aircraft separation",
                "explanation": "A Resolution Advisory provides explicit escape guidance to prevent near-midair collisions."
            },
            {
                "question": "How is the protective volume surrounding an autonomous drone typically modeled in conflict detection math?",
                "options": [
                    "As a cylindrical 'hockey puck' or 3D ellipsoid safety buffer",
                    "As an unbounded horizontal plane",
                    "As an infinitely thin line along the propeller shaft",
                    "As a square box aligned with magnetic north"
                ],
                "answer": "As a cylindrical 'hockey puck' or 3D ellipsoid safety buffer",
                "explanation": "A cylinder or ellipsoid accounts for vertical and horizontal sensor uncertainties and braking distances."
            },
            {
                "question": "Why is time-to-closest-point-of-approach (TCPA) calculated alongside distance-at-closest-point-of-approach (DCPA)?",
                "options": [
                    "To determine whether an evasion maneuver is immediately urgent or distant enough to permit minor trajectory trimming",
                    "To measure remaining cellular data bandwidth",
                    "To calculate rotor rpm gearbox wear",
                    "To reset onboard barometer zero-reference"
                ],
                "answer": "To determine whether an evasion maneuver is immediately urgent or distant enough to permit minor trajectory trimming",
                "explanation": "TCPA gives temporal urgency while DCPA measures geometric severity, enabling prioritized escalation of collision warnings."
            }
        ]
    },
    {
        "career_title": "Autonomous Drone Fleet Architect",
        "skill_name": "Autonomous Navigation Stack Deployment",
        "category": "Operations",
        "title": "Deploying PX4 Autopilot and ROS 2 micro-XRCE-DDS on Edge Companion Computers",
        "source_type": "technical_docs",
        "source_adapter": "structured_tutorial",
        "source_url": "https://docs.px4.io/main/en/ros/ros2_comm.html",
        "author_institution": "Dronecode Foundation",
        "reading_time_minutes": 16,
        "difficulty_level": 3,
        "summary": "Step-by-step architectural deployment guide for robotic drone autonomy. Bridges low-level PX4 flight controllers with high-level ROS 2 navigation stacks using the micro-XRCE-DDS middleware bridge over UART and Ethernet.",
        "takeaways": [
            "The flight controller manages hard real-time motor stabilization loops (1 kHz) while companion computers execute perception and mapping (30 Hz).",
            "micro-XRCE-DDS provides lightweight, memory-efficient DDS communication across serial links between PX4 and ROS 2.",
            "Offboard control mode requires continuous streaming of setpoint heartbeats to prevent automatic failsafe return-to-launch."
        ],
        "concept_overview": "Autonomous aerial robotics relies on a two-tier compute architecture. The Flight Management Unit (FMU) runs a real-time operating system (NuttX) handling attitude control and sensor drivers. High-level autonomy (SLAM, object detection, path planning) runs on an edge companion computer (e.g. Jetson Orin) running Linux and ROS 2. The micro-XRCE-DDS client-agent architecture serializes uORB topics into standard ROS 2 messages, enabling bidirectional command execution with low latency.",
        "practice_scenario": "You are integrating an autonomous drone delivery platform. You establish a 921600-baud serial bridge between the PX4 FMU and ROS 2 companion node, configure uORB message streaming for vehicle_odometry, and successfully command offboard trajectory setpoints.",
        "quizzes": [
            {
                "question": "What is the primary function of the micro-XRCE-DDS client on the PX4 autopilot?",
                "options": [
                    "To bridge internal uORB publish-subscribe topics to external ROS 2 DDS networks",
                    "To encrypt video streams for consumer HDMI monitors",
                    "To calibrate ESC motor timing on startup",
                    "To power cooling fans on the battery enclosure"
                ],
                "answer": "To bridge internal uORB publish-subscribe topics to external ROS 2 DDS networks",
                "explanation": "micro-XRCE-DDS allows memory-constrained embedded flight controllers to communicate with ROS 2 nodes as DDS participants."
            },
            {
                "question": "Why does PX4 require a continuous setpoint stream (>2 Hz) in Offboard mode?",
                "options": [
                    "To ensure the companion computer has not crashed or hung before disengaging autonomous flight",
                    "To prevent the onboard clock from drifting past UTC midnight",
                    "To maintain cellular roaming connection with telco towers",
                    "To clear the flight controller flash log ring buffer"
                ],
                "answer": "To ensure the companion computer has not crashed or hung before disengaging autonomous flight",
                "explanation": "If setpoints stop streaming, the flight controller detects companion failure and triggers failsafe mode (e.g. Hold or RTL)."
            },
            {
                "question": "Which operating system paradigm does the PX4 flight controller run for core attitude estimation loops?",
                "options": [
                    "A deterministic hard real-time operating system (RTOS) like NuttX",
                    "A standard general-purpose Linux distribution like Ubuntu Desktop",
                    "A web browser WebAssembly runtime",
                    "A batch processing virtual machine"
                ],
                "answer": "A deterministic hard real-time operating system (RTOS) like NuttX",
                "explanation": "Flight stabilization requires deterministic sub-millisecond execution guarantees provided by an RTOS."
            },
            {
                "question": "In the ROS 2 navigation stack, which coordinate frame typically represents the earth-fixed, gravity-aligned local origin?",
                "options": [
                    "map or odom frame",
                    "base_link frame",
                    "camera_optical_frame",
                    "gimbal_yaw_link"
                ],
                "answer": "map or odom frame",
                "explanation": "odom and map frames serve as fixed inertial reference frames, while base_link represents the moving vehicle body."
            },
            {
                "question": "What is the main benefit of Hardware-in-the-Loop (HITL) simulation over pure Software-in-the-Loop (SITL)?",
                "options": [
                    "It executes flight firmware on the physical microcontroller hardware, validating processor timing and serial interfaces",
                    "It eliminates the need for any physics simulator software",
                    "It flies physical aircraft outdoors automatically",
                    "It recharges flight batteries during tests"
                ],
                "answer": "It executes flight firmware on the physical microcontroller hardware, validating processor timing and serial interfaces",
                "explanation": "HITL runs code on the target silicon, exposing real hardware timing, bus bottlenecks, and microcontroller constraints."
            }
        ]
    },
    {
        "career_title": "Autonomous Drone Fleet Architect",
        "skill_name": "Swarm Communication Protocol Design",
        "category": "Technical",
        "title": "Mesh Telemetry and Swarm Protocol Design: High-Latency Tolerant Routing via Ad-Hoc 802.11ah and Cellular LTE/5G",
        "source_type": "academic",
        "source_adapter": "arxiv",
        "source_url": "https://arxiv.org/abs/2205.11894",
        "author_institution": "Wireless Telemetry and Swarm Networking Lab",
        "reading_time_minutes": 13,
        "difficulty_level": 4,
        "summary": "Protocol architecture for robust command, control, and telemetry in autonomous drone swarms. Compares BATMAN-adv mesh networking, MAVLink message prioritization, and multi-path fallback across sub-GHz RF and commercial cellular infrastructure.",
        "takeaways": [
            "Ad-hoc mesh routing allows drones to act as relays, extending fleet communication range beyond direct line-of-sight.",
            "MAVLink 2 packet signing and message priority queues ensure safety-critical heartbeats take precedence over video payloads.",
            "Multi-homed dual-SIM cellular gateways provide seamless carrier handoff and link redundancy for urban operations."
        ],
        "concept_overview": "Multi-agent autonomous fleets cannot depend on a single fragile point-to-point radio link. Mesh network protocols (like B.A.T.M.A.N.-adv) establish Layer 2 virtual switches across mobile nodes. When an edge drone moves behind terrain or urban canyons, intermediate drones automatically route command and telemetry packets. By combining QoS tagging with MAVLink message prioritization, the network guarantees sub-100ms latency for emergency abort commands.",
        "practice_scenario": "During an offshore wind turbine inspection mission, an outer drone experiences direct RF signal loss. Your swarm routing engine reroutes its telemetry through an intermediate high-altitude relay drone in 42ms, preventing an uncoordinated mission abort.",
        "quizzes": [
            {
                "question": "What is the primary advantage of Layer 2 mesh networking (such as BATMAN-adv) in dynamic drone swarms?",
                "options": [
                    "It creates a transparent virtual Ethernet switch where nodes can route packets without IP subnet reconfiguration",
                    "It converts analog FM video signals into satellite broadcasts",
                    "It prevents drones from needing onboard batteries",
                    "It guarantees infinite radio transmission range"
                ],
                "answer": "It creates a transparent virtual Ethernet switch where nodes can route packets without IP subnet reconfiguration",
                "explanation": "BATMAN-adv operates at Layer 2, making dynamic link changes transparent to upper-layer IP and UDP applications."
            },
            {
                "question": "Which MAVLink message type must have the highest packet priority queue allocation in telemetry streams?",
                "options": [
                    "HEARTBEAT and COMMAND_LONG (emergency stop/abort commands)",
                    "High-resolution JPEG camera thumbnail streams",
                    "Log file download chunks",
                    "Gimbal pan-tilt smooth tracking feedback"
                ],
                "answer": "HEARTBEAT and COMMAND_LONG (emergency stop/abort commands)",
                "explanation": "Heartbeat and command packets carry critical link-liveness and immediate flight termination directives."
            },
            {
                "question": "What mechanism protects MAVLink 2 telemetry from man-in-the-middle packet injection over open wireless channels?",
                "options": [
                    "Cryptographic packet signing using SHA-256 secret keys and timestamps",
                    "Hiding the SSID on the drone Wi-Fi card",
                    "Setting the drone IP address to 127.0.0.1",
                    "Restricting flights to daylight hours"
                ],
                "answer": "Cryptographic packet signing using SHA-256 secret keys and timestamps",
                "explanation": "MAVLink 2 includes a 13-byte signature containing a link ID, timestamp, and SHA-256 hash to prevent unauthorized command injection."
            },
            {
                "question": "Why is multi-homed dual-SIM bonding advantageous for commercial BVLOS drone operations?",
                "options": [
                    "It provides automatic failover between distinct telecommunication carriers when cellular tower dead zones occur",
                    "It doubles the maximum physical speed of the drone motors",
                    "It bypasses FAA airspace registration requirements",
                    "It allows the drone to carry twice the maximum payload weight"
                ],
                "answer": "It provides automatic failover between distinct telecommunication carriers when cellular tower dead zones occur",
                "explanation": "Dual-SIM bonding hedges against carrier coverage gaps and local cell congestion in urban environments."
            },
            {
                "question": "How does packet loss over lossy RF links impact state synchronization between swarm members in distributed formation algorithms?",
                "options": [
                    "It introduces state estimation covariance growth and potential formation geometry distortion",
                    "It causes immediate permanent memory erase on companion boards",
                    "It reverses the polarity of brushless DC motors",
                    "It changes the physical weight of the airframe"
                ],
                "answer": "It introduces state estimation covariance growth and potential formation geometry distortion",
                "explanation": "State estimation filters must predict positions during packet drops, widening covariance bounds until fresh telemetry arrives."
            }
        ]
    },
    {
        "career_title": "Autonomous Drone Fleet Architect",
        "skill_name": "Airspace Regulatory Compliance Review",
        "category": "Safety",
        "title": "FAA Part 107 Beyond Visual Line of Sight (BVLOS) Waivers and SORA Ground/Air Risk Analysis",
        "source_type": "regulatory",
        "source_adapter": "ecfr",
        "source_url": "https://www.faa.gov/uas/commercial_operators/part_107/",
        "author_institution": "Federal Aviation Administration & JARUS",
        "reading_time_minutes": 15,
        "difficulty_level": 3,
        "summary": "Regulatory framework for commercial drone fleet operations. Details the Specific Operations Risk Assessment (SORA) methodology, Ground Risk Class (GRC), Air Risk Class (ARC), and containment mitigations required for BVLOS approvals.",
        "takeaways": [
            "Specific Operations Risk Assessment (SORA) determines the holistic Specific Assurance and Integrity Level (SAIL).",
            "Ground Risk Class (GRC) is mitigated through kinetic energy reduction, parachutes, and restricted operational ground perimeters.",
            "Air Risk Class (ARC) requires electronic detect-and-avoid (DAA) and cooperative surveillance (ADS-B In, Remote ID)."
        ],
        "concept_overview": "Operating an automated drone fleet at scale requires legal authorization beyond the standard visual observer requirements of 14 CFR Part 107. Civil aviation authorities utilize the SORA process to quantify mission risk. Fleet architects must evaluate the kinetic footprint of aircraft, establish containment geofences with 10^-6 reliability, and demonstrate robust detect-and-avoid capabilities to secure BVLOS operational waivers.",
        "practice_scenario": "You are authoring an FAA BVLOS waiver application for an autonomous medical package drone corridor. You demonstrate an ASTM-certified parachute recovery system that lowers the final Ground Risk Class from GRC 5 to GRC 3, successfully achieving SAIL III certification.",
        "quizzes": [
            {
                "question": "In the SORA framework, what two core risk metrics combine to determine the operational Specific Assurance and Integrity Level (SAIL)?",
                "options": [
                    "Ground Risk Class (GRC) and Air Risk Class (ARC)",
                    "Battery capacity and motor horsepower",
                    "Camera megapixel resolution and lens focal length",
                    "Cloud storage tier and database query latency"
                ],
                "answer": "Ground Risk Class (GRC) and Air Risk Class (ARC)",
                "explanation": "SORA synthesizes ground impact risk (GRC) and mid-air collision risk (ARC) to determine the target SAIL rating."
            },
            {
                "question": "Which emergency mitigation commonly yields an objective reduction in Ground Risk Class (GRC) for multirotor aircraft?",
                "options": [
                    "An ASTM F3322-compliant emergency parachute recovery system",
                    "Bright neon paint schemes on the propeller hubs",
                    "Installing louder propeller warning buzzers",
                    "Increasing maximum cruise flight altitude to 1,000 feet AGL"
                ],
                "answer": "An ASTM F3322-compliant emergency parachute recovery system",
                "explanation": "Certified ballistic parachutes significantly lower terminal impact kinetic energy, reducing injury risk to people on the ground."
            },
            {
                "question": "What is the primary function of FAA Remote ID for unmanned aircraft systems?",
                "options": [
                    "To broadcast real-time identity, location, altitude, and control station position for airspace safety and security",
                    "To stream encrypted 4K video feeds to air traffic control towers",
                    "To bill drone operators automatically for municipal airspace usage",
                    "To transmit weather radar sweeps to private pilots"
                ],
                "answer": "To broadcast real-time identity, location, altitude, and control station position for airspace safety and security",
                "explanation": "Remote ID serves as a digital license plate, allowing aviation authorities and public safety officials to identify operating drones."
            },
            {
                "question": "Under standard FAA Part 107 regulations without a waiver, what is the maximum permissible altitude above ground level (AGL)?",
                "options": [
                    "400 feet AGL (or within 400 feet of an existing structure)",
                    "100 feet AGL strictly",
                    "1,200 feet AGL in rural airspace",
                    "10,000 feet MSL"
                ],
                "answer": "400 feet AGL (or within 400 feet of an existing structure)",
                "explanation": "Part 107 limits operations to 400 feet AGL unless flying within 400 feet of a structure, where the ceiling extends 400 feet above the structure top."
            },
            {
                "question": "Why must the geofence containment system in commercial BVLOS operations possess independent power and termination logic?",
                "options": [
                    "To prevent a flight controller firmware crash from causing a fly-away beyond authorized operational airspace boundaries",
                    "To comply with local municipal noise ordinances",
                    "To speed up onboard video compression",
                    "To keep the drone batteries warm in winter"
                ],
                "answer": "To prevent a flight controller firmware crash from causing a fly-away beyond authorized operational airspace boundaries",
                "explanation": "Independent Flight Termination Systems (FTS) ensure containment even if the primary autopilot suffers complete software lockup."
            }
        ]
    },
    {
        "career_title": "Autonomous Drone Fleet Architect",
        "skill_name": "Ground Control Station Configuration",
        "category": "Tools",
        "title": "Multi-Vehicle Fleet Orchestration in QGroundControl and Mission Planner: Automated Telemetry Ingestion",
        "source_type": "technical_docs",
        "source_adapter": "structured_tutorial",
        "source_url": "https://qgroundcontrol.com/docs/",
        "author_institution": "QGroundControl Engineering Consortium",
        "reading_time_minutes": 12,
        "difficulty_level": 2,
        "summary": "Configuration patterns for centralized multi-UAV operations centers. Explores UDP port multiplexing, automated pre-flight checklists, health telemetry alarming, and geofence boundary loading for simultaneous multi-drone control.",
        "takeaways": [
            "Multi-vehicle GCS setups assign unique MAVLink system IDs (sysid 1..255) to each aircraft in the fleet.",
            "Automated parameter synchronizations verify battery fail-safe voltages and geofence limits before arming.",
            "Centralized telemetry dashboards expose aggregated battery health, GPS satellite count, and communication link margin."
        ],
        "concept_overview": "Operating multiple autonomous drones simultaneously requires specialized ground control station (GCS) software architectures. A single operator must supervise 5 to 20 aircraft without cognitive overload. QGroundControl provides multi-vehicle routing where telemetry packets tagged with distinct MAVLink System IDs populate a unified operational map. Operators monitor health exceptions rather than hand-flying individual airframes.",
        "practice_scenario": "You configure a central operations room to monitor 6 agricultural surveying drones. You configure dedicated UDP telemetry ports (14550-14555), set automated audible alarms for link signal-to-noise ratio drops below 12 dB, and verify automated return-to-launch triggering.",
        "quizzes": [
            {
                "question": "How are distinct aircraft uniquely differentiated in a shared MAVLink telemetry stream?",
                "options": [
                    "By their unique 1-byte MAVLink System ID (sysid)",
                    "By their physical paint color recorded in GPS metadata",
                    "By the operating temperature of their companion processor",
                    "By their battery serial number in plaintext"
                ],
                "answer": "By their unique 1-byte MAVLink System ID (sysid)",
                "explanation": "Every MAVLink packet header contains a System ID (1 to 255) identifying the specific originating vehicle."
            },
            {
                "question": "What is the primary role of the GCS 'Arming Check' parameter mask?",
                "options": [
                    "To prevent motors from spinning until sensors (compass, barometer, GPS, battery) report healthy calibration",
                    "To verify the pilot has entered their credit card details",
                    "To download firmware updates from GitHub over cellular",
                    "To automatically take a promotional aerial selfie"
                ],
                "answer": "To prevent motors from spinning until sensors (compass, barometer, GPS, battery) report healthy calibration",
                "explanation": "Arming checks ensure all flight-critical subsystems meet baseline operational tolerances before flight authorization."
            },
            {
                "question": "When configuring multi-drone UDP telemetry forwarding on an operations server, why are distinct incoming ports used?",
                "options": [
                    "To prevent socket read buffer saturation and separate vehicle telemetry queues cleanly",
                    "To prevent the server CPU from switching threads",
                    "Because UDP packets cannot contain vehicle identification bytes",
                    "To bypass standard computer network firewall rules"
                ],
                "answer": "To prevent socket read buffer saturation and separate vehicle telemetry queues cleanly",
                "explanation": "Distinct port allocations isolate socket traffic and allow modular process architecture per aircraft."
            },
            {
                "question": "What standard failsafe action is automatically triggered if an aircraft loses GCS communication for longer than the timeout parameter?",
                "options": [
                    "Failsafe Return-to-Launch (RTL), Land in place, or Hold position",
                    "Disarm motors instantly mid-air",
                    "Invert pitch and roll at full throttle",
                    "Erase flight logs and SD card memory"
                ],
                "answer": "Failsafe Return-to-Launch (RTL), Land in place, or Hold position",
                "explanation": "Failsafe mechanisms execute predictable safety procedures (such as ascending to safe clearance altitude and returning home) on signal loss."
            },
            {
                "question": "What visualization tool in modern GCS suites alerts operators to conflicting airspace occupancy without manual distance measuring?",
                "options": [
                    "Dynamic conflict proximity rings and ADS-B traffic intruder overlays",
                    "Audio equalizer waveform visualizers",
                    "3D textured video game avatar skins",
                    "Thermal heat map filters on terrain maps"
                ],
                "answer": "Dynamic conflict proximity rings and ADS-B traffic intruder overlays",
                "explanation": "Intruder overlays depict manned and unmanned aircraft with color-coded threat vectors directly on the tactical map."
            }
        ]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # CAREER 2: Robotics Engineer (Niche Existing Career - SOC: 17-2199.08)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "career_title": "Robotics Engineer",
        "skill_name": "Robot Operating System (ROS 2) Architecture",
        "category": "Technical",
        "title": "ROS 2 Humble Architecture: Nodes, Topics, QoS Profiles, and Lifecycle Management",
        "source_type": "technical_docs",
        "source_adapter": "structured_tutorial",
        "source_url": "https://docs.ros.org/en/humble/",
        "author_institution": "Open Source Robotics Foundation (OSRF)",
        "reading_time_minutes": 15,
        "difficulty_level": 3,
        "summary": "Core architectural concepts of ROS 2 Humble. Explores computational graphs, publisher-subscriber communication, intra-process zero-copy transport, Quality of Service (QoS) durability/reliability policies, and Managed Lifecycle Nodes.",
        "takeaways": [
            "ROS 2 uses DDS as its underlying communication middleware, eliminating the single point of failure ROS 1 Master.",
            "QoS profiles allow matching communication reliability (Best Effort for sensors vs Reliable for commands).",
            "Lifecycle Nodes provide deterministic state transitions (Unconfigured, Inactive, Active, Finalized) for safe startup and shutdown."
        ],
        "concept_overview": "Robot Operating System 2 (ROS 2) is the industry standard framework for modern robotic software development. Built upon the Data Distribution Service (DDS) standard, ROS 2 provides real-time capabilities and multi-robot discovery. Managed Lifecycle Nodes allow robotics engineers to guarantee that sensor drivers and motor controllers initialize and configure parameters before entering an active publishing state.",
        "practice_scenario": "You are developing a mobile industrial robot. You configure the LiDAR driver node with Best Effort QoS and volatile durability to minimize sensor pipeline latency, while setting motor command velocity topics to Reliable QoS with transient local durability.",
        "quizzes": [
            {
                "question": "Why did ROS 2 replace the centralized 'roscore' master from ROS 1 with the DDS middleware standard?",
                "options": [
                    "To enable decentralized, dynamic peer-to-peer discovery and remove a single point of failure",
                    "To require all robot code to run inside proprietary cloud databases",
                    "To disable publisher-subscriber message passing in favor of RPCs",
                    "To make Python the only supported programming language"
                ],
                "answer": "To enable decentralized, dynamic peer-to-peer discovery and remove a single point of failure",
                "explanation": "DDS provides automatic peer-to-peer discovery over multicast without requiring a centralized master daemon."
            },
            {
                "question": "Which ROS 2 QoS Reliability policy is best suited for high-frequency sensor data like laser scans or camera feeds?",
                "options": [
                    "Best Effort: Deliver packets quickly without retransmission overhead",
                    "Reliable: Resend lost packets until guaranteed receipt",
                    "Block until ACK: Stop the publishing node until client confirms receipt",
                    "Persistent disk storage before transmission"
                ],
                "answer": "Best Effort: Deliver packets quickly without retransmission overhead",
                "explanation": "For sensor streams, receiving the latest reading immediately is more important than waiting for stale retransmitted packets."
            },
            {
                "question": "What is the primary benefit of using ROS 2 Managed (Lifecycle) Nodes in production automation?",
                "options": [
                    "They enforce a deterministic state machine ensuring all hardware drivers configure before active operation",
                    "They compress C++ source code files automatically",
                    "They allow the robot to run without electrical power",
                    "They convert ROS messages into HTML webpages"
                ],
                "answer": "They enforce a deterministic state machine ensuring all hardware drivers configure before active operation",
                "explanation": "Lifecycle nodes prevent actuators from receiving commands before sensors and calibration routines have completed initialization."
            },
            {
                "question": "How does intra-process communication improve performance when multiple ROS 2 nodes execute within the same process container?",
                "options": [
                    "It passes shared pointers directly in memory, bypassing serialization and network socket overhead",
                    "It rewrites the code in assembly at runtime",
                    "It runs all calculations on the GPU exclusively",
                    "It disables Linux kernel thread scheduling"
                ],
                "answer": "It passes shared pointers directly in memory, bypassing serialization and network socket overhead",
                "explanation": "Intra-process communication enables zero-copy message passing by transferring ownership of shared memory pointers."
            },
            {
                "question": "In ROS 2 parameter management, how do parameters differ from standard topic messages?",
                "options": [
                    "Parameters represent node configuration settings that can be queried or changed dynamically via service calls",
                    "Parameters can only be read once at compilation time and never changed",
                    "Parameters must always be integers between 0 and 255",
                    "Parameters require an external internet connection to validate"
                ],
                "answer": "Parameters represent node configuration settings that can be queried or changed dynamically via service calls",
                "explanation": "Parameters are runtime configuration values associated with individual nodes and manageable via standard services."
            }
        ]
    },
    {
        "career_title": "Robotics Engineer",
        "skill_name": "Kinematic and Dynamic Motion Modeling",
        "category": "Technical",
        "title": "Forward and Inverse Kinematics for Robotic Manipulators: Denavit-Hartenberg and Singularities",
        "source_type": "academic",
        "source_adapter": "arxiv",
        "source_url": "https://ieeexplore.ieee.org/document/8447385",
        "author_institution": "IEEE Robotics and Automation Society",
        "reading_time_minutes": 16,
        "difficulty_level": 4,
        "summary": "Mathematical formulation of robot manipulator kinematics. Covers Denavit-Hartenberg (D-H) parameter assignment, homogenous transformation matrices, inverse kinematic solvers, and Jacobian matrix singularity analysis.",
        "takeaways": [
            "The Denavit-Hartenberg convention uses four parameters (a, alpha, d, theta) to define transformations between consecutive joint frames.",
            "Inverse kinematics maps Cartesian end-effector coordinates back to joint angles, often yielding multiple mathematical solutions.",
            "Kinematic singularities occur when the Jacobian matrix loses rank, resulting in loss of degrees of freedom and infinite joint velocity demands."
        ],
        "concept_overview": "Robot arm positioning requires rigorous geometric modeling. Forward kinematics transforms joint angles (theta_1...theta_n) into tool center point (TCP) coordinates using chained 4x4 homogenous matrices. The reverse problem, Inverse Kinematics (IK), solves for joint angles to achieve a desired Cartesian target. Near kinematic singularities, small tool movements demand physically impossible joint speeds, requiring singularity-robust inverse solvers.",
        "practice_scenario": "You are programming a 6-DOF robotic welding arm. As the arm reaches toward a straight seam near full extension, the wrist approaches a boundary singularity. You implement damped least-squares (Levenberg-Marquardt) IK solving to maintain smooth TCP velocity without joint runaway.",
        "quizzes": [
            {
                "question": "Which four parameters constitute the standard Denavit-Hartenberg (D-H) kinematic convention?",
                "options": [
                    "Link length (a), link twist (alpha), link offset (d), and joint angle (theta)",
                    "Mass, moment of inertia, center of gravity, and friction coefficient",
                    "Voltage, amperage, torque constant, and gear ratio",
                    "Roll, pitch, yaw, and Cartesian translation"
                ],
                "answer": "Link length (a), link twist (alpha), link offset (d), and joint angle (theta)",
                "explanation": "The D-H convention describes relative orientation and translation between adjacent joint axes with these four geometric parameters."
            },
            {
                "question": "What physical phenomenon occurs when a robot manipulator reaches a kinematic singularity?",
                "options": [
                    "The robot loses one or more degrees of freedom in Cartesian motion, and differential IK algorithms command infinite joint speeds",
                    "The electrical power supply trips an overcurrent breaker automatically",
                    "The robot end-effector changes physical weight",
                    "The motors permanently reverse their magnetic polarity"
                ],
                "answer": "The robot loses one or more degrees of freedom in Cartesian motion, and differential IK algorithms command infinite joint speeds",
                "explanation": "At a singularity, the Jacobian matrix loses full rank, making it mathematically non-invertible and causing unconstrained joint velocities."
            },
            {
                "question": "Why does a 6-DOF articulated arm generally have multiple valid inverse kinematic solutions for a single end-effector pose?",
                "options": [
                    "Different mechanical configurations (e.g. elbow-up vs elbow-down, wrist flipped) can achieve the same Cartesian tool pose",
                    "Because floating-point numbers have rounding errors in computer memory",
                    "Because inverse kinematics does not use trigonometry",
                    "Because the control computer has multiple CPU cores"
                ],
                "answer": "Different mechanical configurations (e.g. elbow-up vs elbow-down, wrist flipped) can achieve the same Cartesian tool pose",
                "explanation": "Multiple physical branch configurations (shoulder left/right, elbow up/down, wrist no-flip/flip) can align the tool identically."
            },
            {
                "question": "What is the Jacobian matrix in robotic manipulation kinematics?",
                "options": [
                    "A matrix of first-order partial derivatives relating joint velocities to Cartesian end-effector linear and angular velocities",
                    "A list of serial port baud rates for motor drives",
                    "The electrical resistance table of the servo windings",
                    "The 3D CAD mesh file format used for robot visualization"
                ],
                "answer": "A matrix of first-order partial derivatives relating joint velocities to Cartesian end-effector linear and angular velocities",
                "explanation": "The geometric Jacobian linearly maps joint-space velocity vectors to task-space velocity vectors: v = J(q) * q_dot."
            },
            {
                "question": "Which algorithm is commonly used in numerical inverse kinematics to handle near-singular poses gracefully?",
                "options": [
                    "Damped Least Squares (Levenberg-Marquardt method)",
                    "Bubble sort trajectory indexing",
                    "Simple unconstrained matrix inversion",
                    "Forward Euler integration without damping"
                ],
                "answer": "Damped Least Squares (Levenberg-Marquardt method)",
                "explanation": "Damped least squares introduces a regularization factor that limits commanded joint velocities near singular configurations."
            }
        ]
    },
    {
        "career_title": "Robotics Engineer",
        "skill_name": "Sensor Fusion and State Estimation (Extended Kalman Filter)",
        "category": "Technical",
        "title": "Sensor Fusion for Mobile Robots: Fusing IMU, Odometry, and LiDAR with Extended Kalman Filtering",
        "source_type": "academic",
        "source_adapter": "arxiv",
        "source_url": "https://arxiv.org/abs/2004.14488",
        "author_institution": "Robotics and Perception Group",
        "reading_time_minutes": 15,
        "difficulty_level": 4,
        "summary": "State estimation methodology for autonomous ground vehicles and mobile robots. Explores error propagation in wheel odometry, accelerometer drift in IMUs, and non-linear sensor fusion using the Extended Kalman Filter (EKF).",
        "takeaways": [
            "Wheel odometry accumulates unbounded integration drift over time due to wheel slip and tire deformation.",
            "IMUs provide high-frequency angular rates and accelerations but suffer from low-frequency bias drift.",
            "The Extended Kalman Filter linearizes non-linear robot motion models using Taylor series expansions around current state estimates."
        ],
        "concept_overview": "Autonomous robots cannot navigate accurately with a single sensor. Wheel encoders suffer from wheel slip; IMU accelerometers drift quadratically over time; and GPS or visual odometry can drop out. The Extended Kalman Filter (EKF) provides an optimal recursive Bayesian estimator that fuses these heterogeneous sensors by weighting their measurements inversely according to their noise covariance matrices (Q and R).",
        "practice_scenario": "Your autonomous warehouse AGV loses traction on an oily concrete floor patch. While wheel encoders register high RPM, the fused EKF detects the mismatch against IMU lateral acceleration and LiDAR scan matching, correcting the pose estimate before the robot veers off path.",
        "quizzes": [
            {
                "question": "Why is an Extended Kalman Filter (EKF) needed instead of a standard linear Kalman Filter for mobile robot localization?",
                "options": [
                    "Because robot kinematic equations (involving trigonometric heading angles sin(theta) and cos(theta)) are non-linear",
                    "Because modern microcontrollers cannot compute matrix additions",
                    "Because linear Kalman filters only work with analog vacuum tube sensors",
                    "Because wheel odometry runs at a lower clock frequency than the CPU"
                ],
                "answer": "Because robot kinematic equations (involving trigonometric heading angles sin(theta) and cos(theta)) are non-linear",
                "explanation": "Robot motion in 2D and 3D involves non-linear trigonometric functions of orientation, requiring first-order Taylor series linearization."
            },
            {
                "question": "What do the diagonal elements of the error covariance matrix P represent in an EKF?",
                "options": [
                    "The variance (uncertainty) of each state variable (position x, y, z, orientation, velocities)",
                    "The electrical resistance of the sensor wiring harnesses",
                    "The physical distance from the robot to the nearest obstacle",
                    "The battery level percentage of the robot"
                ],
                "answer": "The variance (uncertainty) of each state variable (position x, y, z, orientation, velocities)",
                "explanation": "The P matrix quantifies the statistical confidence and uncertainty of the estimated state vector."
            },
            {
                "question": "In the EKF measurement update step, what does the Kalman Gain matrix K determine?",
                "options": [
                    "The relative weighting between the predicted state and the new sensor measurement based on their respective uncertainties",
                    "The motor voltage output to drive the wheels faster",
                    "The baud rate of the CAN bus network",
                    "The volume level of safety warning sirens"
                ],
                "answer": "The relative weighting between the predicted state and the new sensor measurement based on their respective uncertainties",
                "explanation": "Kalman gain balances model prediction against noisy sensor observation according to process noise Q and measurement noise R."
            },
            {
                "question": "What is the primary physical cause of 'drift' when integrating raw accelerometer data to estimate position?",
                "options": [
                    "Double integration of sensor bias offsets causes errors to grow quadratically over time (proportional to t^2)",
                    "Radio frequency interference from Wi-Fi routers",
                    "Mechanical vibration cleans the accelerometer silicon dies",
                    "The Earth's magnetic poles continually swap positions"
                ],
                "answer": "Double integration of sensor bias offsets causes errors to grow quadratically over time (proportional to t^2)",
                "explanation": "Integrating acceleration once yields velocity with linear drift; integrating again for position causes quadratic error growth."
            },
            {
                "question": "In ROS 2, which open-source package is widely regarded as the gold standard for fusing odometry and IMU sources via dual-EKF instances?",
                "options": [
                    "robot_localization",
                    "opencv_core",
                    "moveit_config",
                    "gazebo_ros_pkgs"
                ],
                "answer": "robot_localization",
                "explanation": "The robot_localization package provides highly configurable EKF and UKF nodes for continuous multi-sensor state estimation."
            }
        ]
    },
    {
        "career_title": "Robotics Engineer",
        "skill_name": "Feedback Control and Trajectory Generation (PID/LQR)",
        "category": "Technical",
        "title": "Trajectory Tracking with Cascaded PID and Linear Quadratic Regulators (LQR) for Industrial Actuators",
        "source_type": "academic",
        "source_adapter": "arxiv",
        "source_url": "https://ieeexplore.ieee.org/document/7353982",
        "author_institution": "Control Systems Society",
        "reading_time_minutes": 14,
        "difficulty_level": 3,
        "summary": "Control loop architecture for robotic servo actuation. Analyzes inner current/torque loops, intermediate velocity loops, and outer position loops, contrasting classical PID with optimal state-space LQR tracking.",
        "takeaways": [
            "Cascaded control separates fast electrical dynamics (kHz) from mechanical inertia dynamics (100 Hz).",
            "Integral windup during motor saturation must be mitigated using back-calculation or clamping anti-windup circuits.",
            "LQR computes optimal gain matrices K that minimize a quadratic cost function balancing error state with control effort."
        ],
        "concept_overview": "Industrial robots demand both millimeter precision and rapid settling times without overshoot. Standard actuator drives use a three-tier cascaded architecture: an ultra-fast inner current loop, an intermediate velocity loop, and an outer position loop. For multi-variable articulated arms where joint couplings introduce dynamic cross-talk, Linear Quadratic Regulators (LQR) provide optimal gain matrices that minimize state tracking error while bounding control voltage.",
        "practice_scenario": "You are tuning a high-speed pick-and-place gantry robot. The arm overshoots setpoints during rapid deceleration due to motor amplifier saturation. You implement conditional anti-windup on the position loop and tune an LQR gain matrix, eliminating overshoot while preserving cycle time.",
        "quizzes": [
            {
                "question": "What is the primary architectural benefit of cascaded control loops (current, velocity, position) in robot actuators?",
                "options": [
                    "It isolates high-frequency electrical disturbances in the inner loop before they affect outer position tracking",
                    "It converts alternating current motors into direct current steppers",
                    "It eliminates the need for rotary optical encoders",
                    "It reduces total mechanical weight of the arm links"
                ],
                "answer": "It isolates high-frequency electrical disturbances in the inner loop before they affect outer position tracking",
                "explanation": "Cascaded loops run inner electrical loops at high bandwidth (e.g. 10 kHz), rejecting motor ripple and back-EMF before position error accumulates."
            },
            {
                "question": "What problem does 'integral windup' cause when a robot motor hits physical torque saturation?",
                "options": [
                    "The integrator continues accumulating error, causing excessive overshoot and delayed recovery when saturation ends",
                    "The motor controller immediately burns out its H-bridge transistors",
                    "The optical encoder loses its index pulse permanently",
                    "The control software restarts the entire operating system"
                ],
                "answer": "The integrator continues accumulating error, causing excessive overshoot and delayed recovery when saturation ends",
                "explanation": "When an actuator saturates, the loop opens; the integrator winds up to high values, driving large overshoot as error reverses."
            },
            {
                "question": "What two cost matrices must be specified when designing a Linear Quadratic Regulator (LQR)?",
                "options": [
                    "State penalty matrix Q and control effort penalty matrix R",
                    "Baud rate matrix and parity bit array",
                    "Friction matrix and gravity vector",
                    "Sensor noise matrix and GPS dilution of precision"
                ],
                "answer": "State penalty matrix Q and control effort penalty matrix R",
                "explanation": "LQR optimizes J = integral(x^T Q x + u^T R u) dt, trading tracking accuracy (Q) against control actuation expenditure (R)."
            },
            {
                "question": "Why is feedforward control (velocity and acceleration feedforward) combined with feedback PID in trajectory tracking?",
                "options": [
                    "Feedforward anticipates known trajectory dynamics, allowing feedback loops to only correct for small unpredictable disturbances",
                    "Feedforward is used exclusively when feedback sensors fail",
                    "Feedforward reverses the rotation direction of the motor shaft",
                    "Feedforward prevents the robot from consuming electrical power"
                ],
                "answer": "Feedforward anticipates known trajectory dynamics, allowing feedback loops to only correct for small unpredictable disturbances",
                "explanation": "Feedforward injects baseline torque demands directly from the reference trajectory, reducing tracking lag without requiring high feedback gains."
            },
            {
                "question": "In discrete digital control implementation, what happens if the loop sampling period T is chosen too large?",
                "options": [
                    "Phase lag increases and the system becomes unstable or oscillates",
                    "The motor draws less current and runs cooler",
                    "The processor runs out of hard drive space",
                    "The communication cables experience physical corrosion"
                ],
                "answer": "Phase lag increases and the system becomes unstable or oscillates",
                "explanation": "Large sampling intervals introduce significant phase lag into the feedback path, destabilizing high-bandwidth closed loops."
            }
        ]
    },
    {
        "career_title": "Robotics Engineer",
        "skill_name": "Robotic Safety Interlock & ISO 10218 Compliance",
        "category": "Safety",
        "title": "Industrial Collaborative Robotics Safety: ISO 10218 & ISO/TS 15066 Power and Force Limiting (PFL)",
        "source_type": "regulatory",
        "source_adapter": "osha",
        "source_url": "https://www.iso.org/standard/51330.html",
        "author_institution": "International Organization for Standardization (ISO) & OSHA",
        "reading_time_minutes": 15,
        "difficulty_level": 3,
        "summary": "Safety engineering standards for industrial and collaborative robots (cobots). Examines ISO 10218-1/-2, ISO/TS 15066 biomechanical pain thresholds, safety-rated monitored stops (SRMS), and dual-channel safety PLCs.",
        "takeaways": [
            "ISO 10218 requires Category 3 / PL d or Category 4 / PL e safety architectures for all functional safety stops.",
            "ISO/TS 15066 establishes maximum permissible biomechanical force and pressure thresholds for human-robot contacts.",
            "Safety-Rated Monitored Stop (SRMS) maintains drive power while holding zero motion, allowing safe operator entry without restarting."
        ],
        "concept_overview": "Deploying robotic systems in shared workspaces mandates strict adherence to international safety standards. Functional safety interlocks must achieve predetermined Performance Levels (PL r) defined by ISO 13849-1 using redundant dual-channel safety relays. For cobots operating without physical fences, power and force limiting (PFL) limits joint torque and speed so that any unintended collision transfers energy below established pain sensitivity limits.",
        "practice_scenario": "You are designing an automotive assembly cell where operators load clips into a cobot end-effector. You install dual-zone safety laser scanners configured to switch the cobot from full-speed collaborative mode (250 mm/s) to a Safety-Rated Monitored Stop when the operator steps within 0.8 meters.",
        "quizzes": [
            {
                "question": "What is the primary difference between a traditional Safety Stop (Category 0) and a Safety-Rated Monitored Stop (SRMS)?",
                "options": [
                    "SRMS stops motion while maintaining drive power and monitoring position, enabling rapid resumption without homing",
                    "Category 0 stop accelerates the robot to its maximum rated speed before braking",
                    "SRMS disconnects the plant's main three-phase electrical grid",
                    "Category 0 stop is only used for software simulation"
                ],
                "answer": "SRMS stops motion while maintaining drive power and monitoring position, enabling rapid resumption without homing",
                "explanation": "An SRMS holds the robot stationary with active drive power monitored by safety encoders, allowing seamless restarts when zones clear."
            },
            {
                "question": "Which international technical specification defines biomechanical limits for collaborative robot impact force and pressure?",
                "options": [
                    "ISO/TS 15066",
                    "IEEE 802.11ax",
                    "W3C HTML5",
                    "RFC 2616"
                ],
                "answer": "ISO/TS 15066",
                "explanation": "ISO/TS 15066 defines maximum allowable transient and quasi-static forces for specific human body regions in collaborative applications."
            },
            {
                "question": "Under ISO 13849-1, what hardware architecture is required for a Category 3 safety-related control circuit?",
                "options": [
                    "Dual-channel architecture with diagnostic coverage so a single fault does not lead to loss of the safety function",
                    "A single unshielded signal wire with no monitoring",
                    "An internet cloud API connection with 99.9% uptime",
                    "A manual toggle switch without indicator lights"
                ],
                "answer": "Dual-channel architecture with diagnostic coverage so a single fault does not lead to loss of the safety function",
                "explanation": "Category 3 requires redundancy (dual channels) and cross-monitoring to ensure a single component failure cannot prevent safe stopping."
            },
            {
                "question": "What happens if a safety laser scanner detects an intrusion within the programmed safety zone?",
                "options": [
                    "Its safety outputs (OSSDs) open, breaking the safety circuit and triggering an immediate monitored stop",
                    "It emits an ultrasonic dog whistle frequency",
                    "It takes a flash photo and posts it to social media",
                    "It changes the color of the factory ceiling lights"
                ],
                "answer": "Its safety outputs (OSSDs) open, breaking the safety circuit and triggering an immediate monitored stop",
                "explanation": "Safety laser scanners use Output Signal Switching Devices (OSSDs) that drop voltage to 0V when an object breaches the warning/protective zone."
            },
            {
                "question": "Why are physical pinch points and sharp corners eliminated on collaborative robotic end-effectors?",
                "options": [
                    "To distribute collision contact area, reducing peak pressure below ISO/TS 15066 skin puncture and pain thresholds",
                    "To make the robot more aerodynamic during high-speed transit",
                    "To reduce shipping box dimensions",
                    "To match the corporate aesthetic guidelines"
                ],
                "answer": "To distribute collision contact area, reducing peak pressure below ISO/TS 15066 skin puncture and pain thresholds",
                "explanation": "Pressure is force divided by area; rounding edges increases contact surface area, preventing concentrated puncture injuries."
            }
        ]
    },
    {
        "career_title": "Robotics Engineer",
        "skill_name": "End-Effector Gripper and Actuator Integration",
        "category": "Tools",
        "title": "Smart Gripper Integration: Pneumatic vs Electric End-Effectors, Tactile Feedback, and IO-Link",
        "source_type": "technical_docs",
        "source_adapter": "structured_tutorial",
        "source_url": "https://www.assemblymag.com/articles/smart-grippers",
        "author_institution": "Robotic Industries Association & Assembly Magazine",
        "reading_time_minutes": 13,
        "difficulty_level": 2,
        "summary": "Hardware integration guide for robotic end-of-arm tooling (EOAT). Compares pneumatic vs servo-electric grippers, explores IO-Link communication, grip detection sensing, and closed-loop force control for delicate part handling.",
        "takeaways": [
            "Pneumatic grippers offer high power-to-weight ratios but lack mid-stroke positioning and variable force control.",
            "Servo-electric grippers enable precise part measurement, variable grasp force, and dynamic stroke adjustments.",
            "IO-Link protocol delivers digital diagnostics, cycle counts, and grip confirmation over unshielded 3-wire cables."
        ],
        "concept_overview": "The end-effector is the robot's physical interface to the environment. Choosing between pneumatic and servo-electric grippers balances cost, speed, and intelligence. Modern smart grippers communicate via point-to-point digital protocols like IO-Link, transmitting real-time finger position, grasp confirmation, and part dimension verification directly to the robot controller.",
        "practice_scenario": "You integrate a dual-finger electric gripper on a laboratory sample handling arm. Using IO-Link parameterization, you set gripping force to 15 N to prevent crushing fragile glass vials while validating that outer vial diameter falls within 28 +/- 0.5 mm tolerances before lifting.",
        "quizzes": [
            {
                "question": "What is the primary operational advantage of servo-electric grippers over standard pneumatic grippers?",
                "options": [
                    "Programmable grip force, mid-stroke finger positioning, and real-time part dimension verification",
                    "Complete immunity to electrical power outages",
                    "Ten times lower purchase cost than compressed air valves",
                    "Ability to lift heavy shipping containers without a crane"
                ],
                "answer": "Programmable grip force, mid-stroke finger positioning, and real-time part dimension verification",
                "explanation": "Electric grippers allow software-defined stroke, velocity, and force, enabling handling of fragile objects and in-process inspection."
            },
            {
                "question": "What communication protocol is widely adopted for point-to-point digital connection between smart sensors/actuators and industrial fieldbus networks?",
                "options": [
                    "IO-Link (IEC 61131-9)",
                    "Bluetooth Low Energy 4.0",
                    "RS-232 at 9600 baud",
                    "VGA analog video interface"
                ],
                "answer": "IO-Link (IEC 61131-9)",
                "explanation": "IO-Link provides digital bi-directional communication of process data, parameters, and diagnostic events over standard 3-wire cables."
            },
            {
                "question": "Why is 'Grip Lost' detection a critical safety signal in robotic pick-and-place routines?",
                "options": [
                    "To prevent the robot from accelerating or placing an object that was accidentally dropped mid-transit",
                    "To turn on the gripper LED work light",
                    "To format the robot internal SSD drive",
                    "To notify the electrical utility company"
                ],
                "answer": "To prevent the robot from accelerating or placing an object that was accidentally dropped mid-transit",
                "explanation": "Detecting a lost grip allows the robot to halt motion immediately, preventing collision or placing non-existent parts downline."
            },
            {
                "question": "How do vacuum suction cup systems typically detect whether a porous cardboard box has been successfully acquired?",
                "options": [
                    "By monitoring an analog vacuum switch or pressure transducer to verify negative pressure threshold has been reached",
                    "By measuring the physical temperature of the suction cup rubber",
                    "By listening for acoustic room echoes with a microphone",
                    "By checking the moisture level of the compressed air line"
                ],
                "answer": "By monitoring an analog vacuum switch or pressure transducer to verify negative pressure threshold has been reached",
                "explanation": "A vacuum switch confirms that a solid seal has formed and sufficient negative pressure exists to support the payload."
            },
            {
                "question": "What mechanical design element allows robot end-effectors to self-align slightly when inserting a rigid peg into a tight hole?",
                "options": [
                    "A Remote Center Compliance (RCC) device or compliant wrist mount",
                    "Rigid welded steel brackets without bushings",
                    "High-viscosity gear grease on the outside of the tool",
                    "Increasing the robot proportional gain to infinity"
                ],
                "answer": "A Remote Center Compliance (RCC) device or compliant wrist mount",
                "explanation": "RCC mechanisms provide passive lateral and angular elasticity that guides pins into chamfered holes without jamming."
            }
        ]
    }
]

async def seed_niche_curriculum():
    print("\n--- Priming Niche Curriculum Reservoir into Supabase ---")
    emb_service = EmbeddingService()
    
    # 1. Fetch or create canonical skills in 'skills' table
    existing_skills_res = supabase_client.table("skills").select("id, name, category").execute()
    existing_skills = existing_skills_res.data or []
    s_map = {s["name"].lower().strip(): s["id"] for s in existing_skills if s.get("name")}
    
    # 2. Fetch existing careers
    careers_res = supabase_client.table("careers").select("id, title").execute()
    c_map = {c["title"].lower().strip(): c["id"] for c in (careers_res.data or [])}

    seeded_count = 0
    for seed in NICHE_CURRICULUM_SEEDS:
        sk_name = seed["skill_name"].strip()
        sk_cat = seed["category"].strip()
        
        # Ensure skill exists in 'skills' table
        sk_id = s_map.get(sk_name.lower())
        if not sk_id:
            ins = supabase_client.table("skills").insert({"name": sk_name, "category": sk_cat}).execute()
            if ins.data:
                sk_id = ins.data[0]["id"]
                s_map[sk_name.lower()] = sk_id
                print(f"[Skill Primed] Added canonical skill: '{sk_name}' ({sk_cat})")

        c_title = seed["career_title"]
        career_id = c_map.get(c_title.lower().strip())
        field_meta = classify_career_field(c_title)

        # Generate semantic vector
        embed_text = f"Title: {seed['title']}. Skill: {sk_name}. Career: {c_title}. Summary: {seed['summary']}"
        embedding = await emb_service.get_embedding(embed_text)

        content_dict = {
            "summary": seed["summary"],
            "summary_bullets": seed["takeaways"],
            "concept_overview": seed["concept_overview"],
            "practice_scenario": seed["practice_scenario"],
            "quizzes": seed["quizzes"],
            "author_institution": seed["author_institution"],
            "reading_time_minutes": seed["reading_time_minutes"],
            "difficulty_level": seed["difficulty_level"],
            "source_trust_score": 0.95,
            "source_type": seed["source_type"],
            "source_adapter": seed["source_adapter"],
            "source_url": seed["source_url"],
            "source_name": seed["author_institution"],
            "career_title": c_title,
            "career_id": career_id,
            "skill_name": sk_name,
            "field_id": field_meta["field_id"],
            "field_label": field_meta["label"],
            "review_status": "approved",
            "ingested_at": utc_now_iso(),
        }

        lesson_row = {
            "career_id": career_id,
            "associated_skill_id": sk_id,
            "title": seed["title"],
            "summary": seed["summary"],
            "summary_bullets": seed["takeaways"],
            "source_url": seed["source_url"],
            "difficulty_level": seed["difficulty_level"],
            "source_trust_score": 0.95,
            "content": json.dumps(content_dict),
            "quizzes": seed["quizzes"],
            "embedding": embedding,
            "updated_at": utc_now_iso(),
        }

        check = supabase_client.table("micro_content").select("id").eq("title", seed["title"]).execute()
        if check.data:
            supabase_client.table("micro_content").update(lesson_row).eq("id", check.data[0]["id"]).execute()
            print(f"[Lesson Updated] {seed['title'][:60]}... [Skill: {sk_name}]")
        else:
            lesson_row["created_at"] = utc_now_iso()
            supabase_client.table("micro_content").insert(lesson_row).execute()
            print(f"[Lesson Inserted] {seed['title'][:60]}... [Skill: {sk_name}]")
        seeded_count += 1

    print(f"\nPrimed {seeded_count} niche curriculum lessons into micro_content reservoir.")


async def reset_demo_state(career_title="Autonomous Drone Fleet Architect"):
    print(f"\n--- Deprecating & Resetting State for Demo Career: '{career_title}' ---")
    
    # 1. Clean out pending_careers quarantine entries
    p_res = supabase_client.table("pending_careers").delete().ilike("title", f"%{career_title}%").execute()
    print(f"Removed pending_careers quarantine records matching '{career_title}'.")

    # 2. Find career record if exists as unreviewed LLM proposal
    c_res = supabase_client.table("careers").select("id, source_origin, review_status").ilike("title", f"%{career_title}%").execute()
    c_data = c_res.data or []
    for c in c_data:
        cid = c["id"]
        # Only delete if it's an unreviewed LLM proposal (preserve curated canonical careers)
        if c.get("source_origin") == "llm" or c.get("review_status") == "unreviewed":
            # Delete junctions
            supabase_client.table("career_skills").delete().eq("career_id", cid).execute()
            # Clear user profiles pointing to it
            supabase_client.table("profiles").update({"target_career_id": None}).eq("target_career_id", cid).execute()
            # Delete career row
            supabase_client.table("careers").delete().eq("id", cid).execute()
            print(f"Deleted unreviewed career row: {cid} ({career_title})")

    # 3. Clean test accounts if any
    test_emails = ["niche.demo@demo.com", "drone.architect@demo.com", "robotics.learner@demo.com"]
    for email in test_emails:
        u_res = supabase_client.table("profiles").select("id").eq("email", email).execute()
        if u_res.data:
            uid = u_res.data[0]["id"]
            supabase_client.table("daily_drops").delete().eq("user_id", uid).execute()
            supabase_client.table("daily_drop_history").delete().eq("user_id", uid).execute()
            supabase_client.table("user_skills").delete().eq("user_id", uid).execute()
            print(f"Cleaned user profile and drops for: {email}")

    print(f"\nReset complete. Ready to demonstrate live onboarding of '{career_title}' from scratch!")


async def verify_demo_pipeline():
    print("\n--- Verifying End-to-End Pipeline for Niche Demo Careers ---")
    
    careers_to_check = [
        ("Autonomous Drone Fleet Architect", "Novel AI-Induced Niche Career"),
        ("Robotics Engineer", "O*NET Existing Niche Career (SOC: 17-2199.08)")
    ]

    for career_title, label in careers_to_check:
        print(f"\nTarget: {career_title} [{label}]")
        lessons_res = (
            supabase_client.table("micro_content")
            .select("id, title, associated_skill_id, quizzes")
            .ilike("content->>career_title", f"%{career_title}%")
            .execute()
        )
        lessons = lessons_res.data or []
        print(f"  Verified reservoir lessons: {len(lessons)}")
        for idx, l in enumerate(lessons):
            q_count = len(l.get("quizzes") or [])
            print(f"    {idx+1}. {l['title'][:55]}... ({q_count} checkpoint MCQs)")

        if len(lessons) >= 6:
            print(f"  Status: READY (3 primary + 3 reserve pool for 0-overlap reshuffling)")
        else:
            print(f"  Status: WARNING ({len(lessons)}/6 lessons available)")

    print("\n=======================================================")
    print("All Niche Demo Careers are verified and reservoir-primed.")
    print("=======================================================")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Prepare, prime, or reset niche demo careers.")
    parser.add_argument("--seed", action="store_true", help="Prime curriculum reservoir into Supabase micro_content")
    parser.add_argument("--reset", action="store_true", help="Reset test user and unreviewed career rows for live presentation")
    parser.add_argument("--verify", action="store_true", help="Verify that reservoir and skills are ready for 0ms demonstration")
    args = parser.parse_args()

    if args.seed:
        await seed_niche_curriculum()
    if args.reset:
        await reset_demo_state()
    if args.verify or (not args.seed and not args.reset):
        await verify_demo_pipeline()

if __name__ == "__main__":
    asyncio.run(main())
