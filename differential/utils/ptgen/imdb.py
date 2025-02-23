from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List

from differential.utils.ptgen.base import PTGenData, Person, DataType

@dataclass
class IMDBReleaseDate:
    """ For IMDB 'release_date' items: { 'country': ..., 'date': ... } """
    country: Optional[str] = None
    date: Optional[str] = None

    @staticmethod
    def from_dict(obj: Dict[str, Any]) -> 'IMDBReleaseDate':
        return IMDBReleaseDate(
            country=obj.get('country'),
            date=obj.get('date')
        )

@dataclass
class IMDBAka:
    """ For IMDB 'aka' items: { 'country': ..., 'title': ... } """
    country: Optional[str] = None
    title: Optional[str] = None

    @staticmethod
    def from_dict(obj: Dict[str, Any]) -> 'IMDBAka':
        return IMDBAka(
            country=obj.get('country'),
            title=obj.get('title')
        )


@dataclass
class IMDBData(PTGenData):
    """ Dataclass for data returned from imdb.js """
    imdb_id: Optional[str] = None
    imdb_link: Optional[str] = None

    name: Optional[str] = None
    genre: List[str] = field(default_factory=list)
    contentRating: Optional[str] = None
    datePublished: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[str] = None
    poster: Optional[str] = None
    year: Optional[str] = None

    # People
    actors: List[Person] = field(default_factory=list)
    directors: List[Person] = field(default_factory=list)
    creators: List[Person] = field(default_factory=list)

    keywords: List[str] = field(default_factory=list)

    # Ratings
    imdb_votes: Optional[int] = None
    imdb_rating_average: Optional[float] = None
    imdb_rating: Optional[str] = None

    # Additional info
    metascore: Optional[int] = None
    reviews: Optional[int] = None
    critic: Optional[int] = None
    popularity: Optional[int] = None
    details: Dict[str, List[str]] = field(default_factory=dict)

    # Release info
    release_date: List[IMDBReleaseDate] = field(default_factory=list)
    aka: List[IMDBAka] = field(default_factory=list)

    @staticmethod
    def from_dict(obj: Dict[str, Any]) -> 'IMDBData':
        base = PTGenData(
            site=obj['site'],
            sid=obj['sid'],
            success=obj.get('success', False),
            error=obj.get('error'),
            format=obj.get('format'),
            type_=DataType.from_str(obj.get('@type'))
        )
        imdb = IMDBData(**base.__dict__)

        imdb.imdb_id = obj.get('imdb_id')
        imdb.imdb_link = obj.get('imdb_link')
        imdb.name = obj.get('name')
        imdb.genre = obj.get('genre', [])
        imdb.contentRating = obj.get('contentRating')
        imdb.datePublished = obj.get('datePublished')
        imdb.description = obj.get('description')
        imdb.duration = obj.get('duration')
        imdb.poster = obj.get('poster')
        imdb.year = obj.get('year')

        # People
        if 'actors' in obj and isinstance(obj['actors'], list):
            imdb.actors = [Person.from_dict(x) for x in obj['actors']]
        if 'directors' in obj and isinstance(obj['directors'], list):
            imdb.directors = [Person.from_dict(x) for x in obj['directors']]
        if 'creators' in obj and isinstance(obj['creators'], list):
            imdb.creators = [Person.from_dict(x) for x in obj['creators']]

        # Ratings
        imdb.keywords = obj.get('keywords', [])
        imdb.imdb_votes = obj.get('imdb_votes')
        imdb.imdb_rating_average = obj.get('imdb_rating_average')
        imdb.imdb_rating = obj.get('imdb_rating')
        imdb.metascore = obj.get('metascore')
        imdb.reviews = obj.get('reviews')
        imdb.critic = obj.get('critic')
        imdb.popularity = obj.get('popularity')
        imdb.details = obj.get('details', {})

        # Release info
        if 'release_date' in obj and isinstance(obj['release_date'], list):
            imdb.release_date = [IMDBReleaseDate.from_dict(r) for r in obj['release_date']]
        if 'aka' in obj and isinstance(obj['aka'], list):
            imdb.aka = [IMDBAka.from_dict(a) for a in obj['aka']]

        return imdb

    def __str__(self) -> str:
        if self.name:
            return self.name
        return super().__str__()
