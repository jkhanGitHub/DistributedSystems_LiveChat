from enum import Enum, auto
class ServerState(Enum):
    LOOKING = "LOOKING"
    FOLLOWER = "FOLLOWER"
    LEADER = "LEADER"
    ELECTION_IN_PROGRESS = "ELECTION_IN_PROGRESS"
